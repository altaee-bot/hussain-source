"""
.يوت — تحميل فيديو/صوت من يوتيوب (وأي موقع يدعمه yt-dlp) مع كيبورد شفاف:
  1) ابحث أو ضع رابط  →  2) اختر 🎬 فيديو أو 🎧 صوت  →  3) اختر الدقة/الصيغة  →  يُرسل الملف.

صيغ مباشرة بدون أزرار:
  .يوت صوت <اسم/رابط>            .يوت فيديو <اسم/رابط> [720]
"""
import asyncio
import os
import re
import time

from telethon import types

from core import bridge, netutil, yt
from core.constants import TMP_ROOT
from core.framework import CmdError, command
from core.ui import human_dur, human_size, progress_bar

AUDIO_WORDS = {"صوت", "mp3", "audio"}
VIDEO_WORDS = {"فيديو", "video", "vid", "مقطع"}
_WARNED = {"inline": False}


class _Status:
    """يحدّث رسالة الحالة: عبر البوت (inline) أو بتعديل رسالة الأمر."""

    def __init__(self, cmd, pending=None, msg=None):
        self.cmd, self.pending, self.msg = cmd, pending, msg
        self._last = 0.0

    async def update(self, text, force=False):
        if self.pending is not None:
            from telethon import Button
            btn = [[Button.inline("❌ إلغاء", f"rc|yt|{self.pending.token}|x")]]
            return await self.pending.edit(text, buttons=btn, force=force)
        now = time.monotonic()
        if not force and now - self._last < 3:
            return False
        self._last = now
        try:
            if self.msg is not None:
                await self.msg.edit(text)
            else:
                self.msg = await self.cmd.edit(text)
        except Exception:
            pass
        return True


def _parse(args):
    """يرجع (kind|None, quality|None, query)."""
    words = args.split()
    if not words:
        return None, None, ""
    head = words[0].lower()
    if head in AUDIO_WORDS:
        return "a", "mp3_192" if yt.has_ffmpeg() else "m4a", " ".join(words[1:])
    if head in VIDEO_WORDS:
        rest = words[1:]
        q = 720
        if rest and re.fullmatch(r"(\d{3,4})p?", rest[-1]) and int(rest[-1].rstrip("p")) in yt.STD_HEIGHTS:
            q = int(rest[-1].rstrip("p"))
            rest = rest[:-1]
        elif rest and re.fullmatch(r"(\d{3,4})p?", rest[0]) and int(rest[0].rstrip("p")) in yt.STD_HEIGHTS:
            q = int(rest[0].rstrip("p"))
            rest = rest[1:]
        return "v", q, " ".join(rest)
    return None, None, args


async def _resolve(cmd, query):
    """يرجع قائمة نتائج [{url,title,...}] من اسم أو رابط."""
    if yt.is_url(query):
        url = yt.extract_url(query)
        info = await asyncio.to_thread(yt.get_info, url)
        r = yt.brief(info)
        r["url"] = url
        return [r], info
    res = await asyncio.to_thread(yt.search, query, 5)
    if not res:
        raise CmdError("ما لقيت نتائج لهذا البحث.")
    return res, None


async def _download_and_send(cmd, status, url, kind, quality, reply_to, cancelled=lambda: False, info=None):
    client, ctx = cmd.client, cmd.ctx
    outdir = os.path.join(TMP_ROOT, f"yt_{ctx.data_dir.rsplit(os.sep, 1)[-1]}_{yt.ts()}")
    hook = yt.ProgressHook()
    hook.cancel_check = cancelled
    label = "🎬 فيديو" if kind == "v" else "🎧 صوت"
    try:
        await status.update(f"⏳ **جاري التحميل...**\n{label}\n`{progress_bar(0)}`", force=True)
        task = asyncio.create_task(asyncio.to_thread(yt.download, url, kind, quality, outdir, hook))
        while not task.done():
            await asyncio.wait([task], timeout=2.5)
            if task.done():
                break
            eta = f" • ⏳ {human_dur(hook.eta)}" if hook.eta else ""
            spd = f" • ⚡ {human_size(hook.speed)}/s" if hook.speed else ""
            tot = f"\n📦 {human_size(hook.done)} / {human_size(hook.total)}" if hook.total else ""
            await status.update(f"⏳ **جاري التحميل...**\n{label}\n`{progress_bar(hook.pct)}`{spd}{eta}{tot}")
        try:
            path, info = task.result()
        except Exception as e:
            if cancelled():
                return False
            raise CmdError(f"فشل التحميل: `{str(e)[:160]}`\n💡 جرّب تحديث المحرك بالأمر `.تحديث_يوت`")

        size = os.path.getsize(path)
        me = await ctx.get_me()
        limit = (4000 if getattr(me, "premium", False) else 2000) * 1024 * 1024
        if size > limit:
            raise CmdError(f"الملف كبير ({human_size(size)}) وأكبر من حد تليجرام. اختر دقة أقل.")

        thumb = None
        if info.get("thumbnail"):
            try:
                data = await netutil.get_bytes(info["thumbnail"], timeout=10)
                thumb = os.path.join(outdir, "thumb.jpg")
                with open(thumb, "wb") as f:
                    f.write(data)
            except Exception:
                thumb = None

        title = info.get("title") or "RECO"
        dur = int(info.get("duration") or 0)
        if kind == "v":
            attrs = [types.DocumentAttributeVideo(duration=dur, w=int(info.get("width") or 0),
                                                  h=int(info.get("height") or 0), supports_streaming=True)]
            cap = f"🎬 **{title}**\n📺 {info.get('height') or quality}p • 📦 {human_size(size)}\n🦅 RECO"
        else:
            attrs = [types.DocumentAttributeAudio(duration=dur, title=title[:60],
                                                  performer=(info.get("uploader") or "RECO")[:40])]
            cap = f"🎧 **{title}**\n📦 {human_size(size)}\n🦅 RECO"

        loop = asyncio.get_running_loop()

        def progress(cur, total):
            if total:
                loop.create_task(status.update(f"🚀 **جاري الرفع...**\n`{progress_bar(cur / total * 100)}`\n"
                                               f"📦 {human_size(cur)} / {human_size(total)}"))

        await status.update("🚀 **جاري الرفع...**", force=True)
        await client.send_file(cmd.chat_id, path, caption=cap, attributes=attrs, thumb=thumb,
                               supports_streaming=(kind == "v"), reply_to=reply_to,
                               progress_callback=progress)
        return True
    finally:
        yt.clean_tmp(outdir)


@command(".يوت", ".تحميل", section="media", usage=".يوت <اسم أو رابط>",
         desc="تحميل فيديو/صوت بأزرار تختار منها النوع والدقة (يدعم يوتيوب وانستا وتيك توك...)")
async def youtube(cmd):
    query = cmd.args
    reply = await cmd.reply_msg()
    if not query and reply is not None:
        query = yt.extract_url(reply.raw_text or "") or ""
    kind, quality, query = _parse(query)
    if not query:
        raise CmdError("اكتب اسم أو رابط بعد الأمر.\n"
                       "`.يوت اسم الاغنية`  |  `.يوت صوت اسم`  |  `.يوت فيديو اسم 720`")
    reply_to = cmd.event.reply_to_msg_id if cmd.event.is_reply else None
    await cmd.edit("🔎 **جاري البحث...**")

    results, info = await _resolve(cmd, query)

    # ── تحميل مباشر بدون أزرار
    if kind:
        status = _Status(cmd)
        sent = await _download_and_send(cmd, status, results[0]["url"], kind, quality, reply_to, info=info)
        if sent:
            await cmd.delete()
        return

    # ── مسار الأزرار الشفافة عبر البوت الرئيسي
    msg = None
    if bridge.available():
        pending = bridge.create(cmd.event.sender_id, cmd.chat_id, "yt", {"results": results, "idx": 0})
        if info:
            pending.data["infos"] = {results[0]["url"]: info}
        msg, why = await bridge.send_inline(cmd.client, cmd.chat_id, f"yt:{pending.token}", reply_to=reply_to)
        if msg is None:
            pending.close()
            if not _WARNED["inline"]:
                _WARNED["inline"] = True
                await cmd.edit(f"⚠️ تعذر عرض الأزرار: {why}\n⏬ راح أحمّل صوت مباشرة هذي المرة...")
                await asyncio.sleep(2.5)
        else:
            await cmd.delete()
            try:
                choice = await pending.wait(180)
                if not choice:
                    await _safe_delete(msg)
                    return
                r = results[choice["idx"]]
                status = _Status(cmd, pending=pending)
                ok = await _download_and_send(cmd, status, r["url"], choice["kind"], choice["quality"], reply_to,
                                              cancelled=lambda: pending.cancelled, info=pending.data.get("infos", {}).get(r["url"]))
                await _safe_delete(msg)
                if not ok:
                    return
            except CmdError as e:
                await pending.edit(f"❌ {e}", buttons=None, force=True)
                await asyncio.sleep(6)
                await _safe_delete(msg)
            except Exception as e:
                await pending.edit(f"❌ خطأ: `{str(e)[:150]}`", buttons=None, force=True)
                await asyncio.sleep(6)
                await _safe_delete(msg)
            finally:
                pending.close()
            return

    # ── احتياطي: صوت مباشرة
    status = _Status(cmd)
    q = "mp3_192" if yt.has_ffmpeg() else "m4a"
    if await _download_and_send(cmd, status, results[0]["url"], "a", q, reply_to):
        await cmd.delete()


async def _safe_delete(msg):
    try:
        await msg.delete()
    except Exception:
        pass


@command(".تحديث_يوت", section="media", desc="تحديث محرك التحميل yt-dlp (يحل أغلب مشاكل التحميل)")
async def update_engine(cmd):
    await cmd.edit("⏳ **جاري تحديث yt-dlp...**")
    ok, tail = await asyncio.to_thread(yt.update_ytdlp)
    if ok:
        await cmd.edit("✅ **تم التحديث.** أعد تشغيل السورس بالأمر `.اعادة_تشغيل` لتفعيل النسخة الجديدة.")
    else:
        await cmd.edit(f"❌ **فشل التحديث:**\n`{tail}`")
