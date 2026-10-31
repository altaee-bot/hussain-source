"""
معالجات البوت الرئيسي (اللي توكنه بـ config.py): نتائج inline + ضغطات الأزرار الشفافة.
يُربط من app.py بسطر واحد:   inline_bot.register(bot)

صيغة بيانات الأزرار (≤ 64 بايت):
    rc|m|<owner>|<رقم القسم أو 0 للرئيسية أو x للإغلاق>      ← قائمة الأوامر
    rc|yt|<token>|<فعل>[|نوع|جودة]                            ← اختيار تحميل يوتيوب
"""
import asyncio
import logging
import re

from telethon import Button, events

from core import bridge, catalog, yt
from core.constants import CHANNEL, DEV_USER, SOURCE_CH
from core.ui import LINE, human_dur, human_size

log = logging.getLogger("reco")
ZW = "\u200b"


def _preview(url):
    return f"[{ZW}]({url})" if url else ""


# ───────────────────────── قائمة الأوامر
def menu_buttons(owner):
    rows, row = [], []
    for num, key, icon, title in catalog.SECTIONS:
        row.append(Button.inline(f"{icon} {title}", f"rc|m|{owner}|{num}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([Button.url("👨‍💻 المطور", f"https://t.me/{DEV_USER.lstrip('@')}"),
                 Button.url("📡 القناة", f"https://t.me/{SOURCE_CH}")])
    rows.append([Button.inline("❌ إغلاق", f"rc|m|{owner}|x")])
    return rows


def menu_back_buttons(owner):
    return [[Button.inline("🔙 القائمة الرئيسية", f"rc|m|{owner}|0"),
             Button.inline("❌ إغلاق", f"rc|m|{owner}|x")]]


# ───────────────────────── شاشات يوتيوب
def yt_main_screen(p):
    res = p.data["results"]
    i = p.data["idx"]
    r = res[i]
    t = p.token
    meta = []
    if r.get("channel"):
        meta.append(f"👤 {r['channel']}")
    if r.get("duration"):
        meta.append(f"⏱ {human_dur(r['duration'])}")
    if r.get("views"):
        meta.append(f"👁 {r['views']:,}")
    text = (f"{_preview(r.get('thumb'))}🎬 **{r['title']}**\n"
            f"{'  •  '.join(meta)}\n{LINE}\n"
            f"👇 **اختر نوع التحميل:**")
    rows = [[Button.inline("🎬 فيديو", f"rc|yt|{t}|v"), Button.inline("🎧 صوت", f"rc|yt|{t}|a")]]
    if len(res) > 1:
        rows.append([Button.inline("⬅️ السابق", f"rc|yt|{t}|p"),
                     Button.inline(f"{i + 1}/{len(res)}", f"rc|yt|{t}|noop"),
                     Button.inline("➡️ التالي", f"rc|yt|{t}|n")])
    rows.append([Button.inline("❌ إغلاق", f"rc|yt|{t}|x")])
    return text, rows


def yt_video_screen(p, info):
    t = p.token
    r = p.data["results"][p.data["idx"]]
    opts = yt.video_options(info)
    rows, row = [], []
    for h, size in opts:
        label = f"🎬 {h}p" + (f" • {human_size(size)}" if size else "")
        row.append(Button.inline(label, f"rc|yt|{t}|go|v|{h}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    if not rows:
        rows.append([Button.inline("🎬 أفضل جودة متاحة", f"rc|yt|{t}|go|v|1080")])
    rows.append([Button.inline("🔙 رجوع", f"rc|yt|{t}|b"), Button.inline("❌ إغلاق", f"rc|yt|{t}|x")])
    note = "" if yt.has_ffmpeg() else "\n⚠️ ffmpeg غير مثبّت: الدقات العالية قد تكون غير متاحة."
    text = (f"{_preview(r.get('thumb'))}🎬 **{r['title']}**\n{LINE}\n"
            f"📺 **اختر دقة الفيديو:**{note}")
    return text, rows


def yt_audio_screen(p, info):
    t = p.token
    r = p.data["results"][p.data["idx"]]
    size = yt.audio_size(info)
    rows = [[Button.inline("🎧 M4A • أسرع" + (f" • {human_size(size)}" if size else ""), f"rc|yt|{t}|go|a|m4a")]]
    if yt.has_ffmpeg():
        rows.append([Button.inline(f"🎵 MP3 {q}", f"rc|yt|{t}|go|a|mp3_{q}") for q in yt.MP3_QUALITIES])
    rows.append([Button.inline("🔙 رجوع", f"rc|yt|{t}|b"), Button.inline("❌ إغلاق", f"rc|yt|{t}|x")])
    text = (f"{_preview(r.get('thumb'))}🎧 **{r['title']}**\n{LINE}\n"
            f"🔊 **اختر صيغة الصوت:**")
    return text, rows


# ───────────────────────── التسجيل
def register(bot):
    @bot.on(events.InlineQuery)
    async def on_inline(event):
        q = (event.text or "").strip()
        b = event.builder
        try:
            if q.startswith("yt:"):
                p = bridge.get(q[3:])
                if not p or p.owner_id != event.sender_id:
                    return await event.answer([], cache_time=0)
                text, rows = yt_main_screen(p)
                r = p.data["results"][p.data["idx"]]
                art = b.article(f"🎬 {r['title'][:60]}", description="اضغط لإرسال قائمة التحميل",
                                text=text, buttons=rows, link_preview=True, parse_mode="md")
                return await event.answer([art], cache_time=0, private=True)
            if q.startswith("menu:"):
                owner = int(q.split(":", 1)[1])
                if owner != event.sender_id:
                    return await event.answer([], cache_time=0)
                art = b.article("🦅 قائمة أوامر ريكو", description="اضغط لإرسال القائمة",
                                text=catalog.main_menu_text(), buttons=menu_buttons(owner),
                                link_preview=False, parse_mode="md")
                return await event.answer([art], cache_time=0, private=True)
            # أي استعلام ثاني: نعرض تعريف بسيط
            art = b.article("🦅 سورس ريكو", description=f"{CHANNEL}",
                            text=f"🦅 **سورس ريكو المطور**\n📡 {CHANNEL}\n👨‍💻 {DEV_USER}",
                            buttons=[[Button.url("📡 القناة", f"https://t.me/{SOURCE_CH}")]], parse_mode="md")
            await event.answer([art], cache_time=60)
        except Exception:
            log.exception("inline query error")

    @bot.on(events.CallbackQuery(data=re.compile(rb"^rc\|")))
    async def on_cb(event):
        try:
            parts = event.data.decode().split("|")
            kind = parts[1]
            if kind == "m":
                await _menu_cb(event, parts)
            elif kind == "yt":
                await _yt_cb(event, parts)
        except Exception:
            log.exception("callback error")
            try:
                await event.answer("⚠️ صار خطأ، أعد المحاولة.", alert=True)
            except Exception:
                pass


async def _menu_cb(event, parts):
    owner = int(parts[2])
    act = parts[3]
    if event.sender_id != owner:
        return await event.answer("⚠️ هذا الزر ليس لك!", alert=True)
    await event.answer()
    if act == "x":
        return await event.edit("🗂 **تم إغلاق القائمة.**  أرسل `.اوامر` لفتحها من جديد.", buttons=None)
    if act == "0":
        return await event.edit(catalog.main_menu_text(), buttons=menu_buttons(owner), link_preview=False)
    await event.edit(catalog.help_text(int(act)), buttons=menu_back_buttons(owner), link_preview=False)


async def _yt_cb(event, parts):
    t, act = parts[2], parts[3]
    p = bridge.get(t)
    if not p:
        return await event.answer("⌛ انتهت صلاحية هذي القائمة، أعد الأمر.", alert=True)
    if event.sender_id != p.owner_id:
        return await event.answer("⚠️ هذا الزر ليس لك!", alert=True)
    if p.inline_id is None:
        p.inline_id = event.query.msg_id

    if act == "noop":
        return await event.answer()
    if act == "x":
        await event.answer("تم الإلغاء")
        p.cancel()
        return await event.edit("✖️ **تم الإلغاء.**", buttons=None)

    if act in ("n", "p", "b"):
        await event.answer()
        n = len(p.data["results"])
        if act == "n":
            p.data["idx"] = (p.data["idx"] + 1) % n
        elif act == "p":
            p.data["idx"] = (p.data["idx"] - 1) % n
        text, rows = yt_main_screen(p)
        return await event.edit(text, buttons=rows, link_preview=True)

    if act in ("v", "a"):
        await event.answer("⏳ لحظة...")
        r = p.data["results"][p.data["idx"]]
        infos = p.data.setdefault("infos", {})
        info = infos.get(r["url"])
        if info is None:
            await event.edit(f"⏳ **أفحص الصيغ المتاحة...**\n🎬 {r['title']}", buttons=None, link_preview=False)
            try:
                info = await asyncio.to_thread(yt.get_info, r["url"])
            except Exception as e:
                text, rows = yt_main_screen(p)
                return await event.edit(f"❌ **تعذر قراءة الفيديو:** `{str(e)[:150]}`\n\n{text}",
                                        buttons=rows, link_preview=False)
            infos[r["url"]] = info
        text, rows = yt_video_screen(p, info) if act == "v" else yt_audio_screen(p, info)
        return await event.edit(text, buttons=rows, link_preview=True)

    if act == "go":
        kind, quality = parts[4], parts[5]
        await event.answer("🚀 بدأ العمل!")
        await event.edit("⏳ **جاري التحضير...**", buttons=[[Button.inline("❌ إلغاء", f"rc|yt|{t}|x")]],
                         link_preview=False)
        p.choose({"kind": kind, "quality": quality, "idx": p.data["idx"]})
