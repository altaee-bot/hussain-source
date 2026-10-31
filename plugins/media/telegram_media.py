"""ميديا تيليجرام: ستوري، منشورات مقيدة، حفظ ميديا (ذاتية التدمير)، أرشفة المحذوفات."""
import os
import re
from datetime import datetime, timedelta

from telethon import events, functions, types

from core.framework import CmdError, command, listener
from core.ui import human_size

STORY_BOT = "@download_story_tele_bot"
STORY_CHANNELS = ["alikwiq_News", "Mintors_tag_bots"]


@command(".ستوري", section="media", usage=".ستوري <رابط الستوري>", desc="تحميل ستوري تليجرام برابطه (بسرية: يغادر القنوات ويحذف المحادثة بعدها)")
async def story(cmd):
    link = cmd.args.strip()
    cmd.need(link, "ضع رابط الستوري بعد الأمر.")
    client = cmd.client
    await cmd.edit("⏳ **جاري العمل بسرية...**")
    joined = []
    try:
        for ch in STORY_CHANNELS:
            try:
                await client(functions.channels.JoinChannelRequest(channel=ch))
                joined.append(ch)
                ent = await client.get_input_entity(ch)
                await client(functions.folders.EditPeerFoldersRequest(
                    folder_peers=[types.InputFolderPeer(peer=ent, folder_id=1)]))
            except Exception:
                pass
        try:
            await client(functions.account.UpdateNotifySettingsRequest(
                peer=STORY_BOT, settings=types.InputPeerNotifySettings(mute_until=2147483647)))
            await client(functions.contacts.UnblockRequest(id=STORY_BOT))
        except Exception:
            pass
        found = False
        async with client.conversation(STORY_BOT, timeout=60) as conv:
            await conv.send_message(link)
            for _ in range(5):
                resp = await conv.get_response()
                if resp.media:
                    await client.send_file(cmd.chat_id, resp.media, caption="✅ **تم تحميل الستوري بواسطة ريكو**")
                    found = True
                    break
        if found:
            await cmd.delete()
        else:
            await cmd.edit("❌ فشل التحميل، تأكد من الرابط (الستوري لازم يكون عام أو أنت تقدر تشوفه).")
    finally:
        for ch in joined:
            try:
                await client(functions.channels.LeaveChannelRequest(channel=ch))
            except Exception:
                pass
        try:
            await client(functions.messages.DeleteHistoryRequest(peer=STORY_BOT, max_id=0, just_clear=False, revoke=True))
            await client(functions.contacts.BlockRequest(id=STORY_BOT))
        except Exception:
            pass


_LINK = re.compile(r"t\.me/(?:c/(\d+)|([A-Za-z]\w{3,31}))/(?:\d+/)?(\d+)")


@command(".مقيد", section="media", usage=".مقيد <رابط المنشور>", desc="جلب منشور (نص/ميديا) من قناة أو مجموعة مقيّدة التحويل")
async def restricted(cmd):
    link = cmd.args.strip()
    cmd.need(link, "ضع رابط المنشور بعد الأمر.")
    m = _LINK.search(link)
    cmd.need(m, "الرابط غير صالح — لازم يشبه `t.me/قناة/123` أو `t.me/c/123456/78`.")
    private_id, username, msg_id = m.group(1), m.group(2), int(m.group(3))
    await cmd.edit("⏳ **جاري جلب المنشور...**")
    ref = int(f"-100{private_id}") if private_id else username
    try:
        msg = await cmd.client.get_messages(ref, ids=msg_id)
    except Exception as e:
        s = str(e)
        if "USER_NOT_PARTICIPANT" in s or "CHANNEL_PRIVATE" in s:
            raise CmdError("أنت مو مشترك بهذي القناة — اشترك فيها أول ثم أعد المحاولة.")
        raise
    cmd.need(msg, "المنشور غير موجود أو انحذف.")
    reply_to = cmd.event.reply_to_msg_id
    if msg.media and not isinstance(msg.media, types.MessageMediaWebPage):
        await cmd.edit("📥 **جاري تحميل الميديا...**")
        path = await cmd.client.download_media(msg)
        cmd.need(path, "فشل تحميل الميديا.")
        try:
            await cmd.client.send_file(cmd.chat_id, path, caption=f"✅ **تم فك القيد** ({human_size(os.path.getsize(path))})\n\n{msg.text or ''}"[:1024],
                                       reply_to=reply_to)
        finally:
            if os.path.exists(path):
                os.remove(path)
        return await cmd.delete()
    cmd.need(msg.text, "المنشور فارغ أو نوعه غير مدعوم.")
    await cmd.client.send_message(cmd.chat_id, msg.text, reply_to=reply_to)
    await cmd.delete()


@command(".حفظ", section="media", usage=".حفظ (بالرد على ميديا)", desc="حفظ الميديا المردود عليها (حتى ذاتية التدمير) برسائلك المحفوظة")
async def save_media(cmd):
    r = await cmd.reply_msg()
    cmd.need(r and r.media, "رد على رسالة فيها ميديا.")
    path = await cmd.client.download_media(r)
    try:
        await cmd.client.send_file("me", path, caption=f"💾 محفوظ من `{r.sender_id}`\n{r.text or ''}"[:1024])
    finally:
        if path and os.path.exists(path):
            os.remove(path)
    await cmd.edit("✅ **تم الحفظ برسائلك المحفوظة.**")


# ───────────────────────── الحفظ التلقائي
@command(".تخزين_الخاص", section="media", usage=".تخزين_الخاص تشغيل|ايقاف",
         desc="تحويل كل رسائل الخاص لمجموعة التخزين (افتراضياً متوقف لتجنب الضغط)")
async def store_pv(cmd):
    on = not (cmd.words[:1] and cmd.words[0] in ("ايقاف", "تعطيل", "off"))
    cmd.ctx.state.set("store_pv", on)
    await cmd.edit(f"📥 تخزين الخاص: {'**شغّال** ✅' if on else '**متوقف** ⛔'}")


@command(".تخزين_الكروبات", section="media", usage=".تخزين_الكروبات تشغيل|ايقاف",
         desc="تحويل رسائل المجموعات لمجموعة التخزين (يستهلك حدود تيليجرام — استعمله بحذر)")
async def store_groups(cmd):
    on = not (cmd.words[:1] and cmd.words[0] in ("ايقاف", "تعطيل", "off"))
    cmd.ctx.state.set("store_groups", on)
    await cmd.edit(f"📥 تخزين المجموعات: {'**شغّال** ✅' if on else '**متوقف** ⛔'}")


@listener(events.NewMessage(incoming=True))
async def media_saver(event, ctx):
    client = ctx.client
    if event.is_private:
        media = event.media
        if media is not None and getattr(media, "ttl_seconds", None):
            path = await event.download_media()
            try:
                cap = f"📥 ميديا ذاتية التدمير من: `{event.sender_id}`"
                await client.send_message("me", cap, file=path)
                if ctx.storage_pv:
                    await client.send_message(ctx.storage_pv, cap, file=path)
            finally:
                if path and os.path.exists(path):
                    os.remove(path)
        elif ctx.state.get("store_pv") and ctx.storage_pv and event.sender_id not in ctx.helpers:
            await client.forward_messages(ctx.storage_pv, event.message)
    elif ctx.state.get("store_groups") and ctx.storage_groups:
        if event.chat_id not in (ctx.storage_pv, ctx.storage_groups, ctx.storage_deleted):
            await client.forward_messages(ctx.storage_groups, event.message)


# ───────────────────────── كشف المحذوفات (خاص)
@listener(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def private_cache(event, ctx):
    ctx.msg_cache[event.id] = {"message": event.message, "expiry": datetime.now() + timedelta(minutes=10)}
    if len(ctx.msg_cache) > 3000:
        now = datetime.now()
        for k in [k for k, v in ctx.msg_cache.items() if v["expiry"] < now]:
            ctx.msg_cache.pop(k, None)


@listener(events.MessageDeleted)
async def deleted_watcher(event, ctx):
    client = ctx.client
    for mid in event.deleted_ids:
        item = ctx.msg_cache.pop(mid, None)
        if not item:
            continue
        old = item["message"]
        target = ctx.storage_deleted or "me"
        sender = await old.get_sender()
        name = getattr(sender, "first_name", None) or "مجهول"
        await client.send_message(target, f"🗑 **رسالة محذوفة** من [{name}](tg://user?id={old.sender_id})\n{old.text or ''}")
        if old.media and not isinstance(old.media, types.MessageMediaWebPage):
            path = None
            try:
                path = await client.download_media(old)
                if path:
                    await client.send_file(target, path)
            except Exception:
                pass
            finally:
                if path and os.path.exists(path):
                    os.remove(path)
