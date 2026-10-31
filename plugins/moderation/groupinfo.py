"""معلومات المجموعة: قائمة المشرفين/البوتات/المقيدين، إحصائيات، رابط، منشن، قفل وفتح."""
import asyncio
import inspect

from telethon import functions
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import (ChannelParticipantsAdmins, ChannelParticipantsBanned, ChannelParticipantsBots,
                               ChatBannedRights)

from core.framework import command
from core.ui import card, kv, mention

_VALID = set(inspect.signature(ChatBannedRights.__init__).parameters) - {"self", "until_date"}


@command(".معلوماته", section="moderation", helpers=True, usage=".معلوماته [رد/@يوزر]", desc="كشف بيانات عضو")
async def user_info(cmd):
    user = await cmd.target()
    full = await cmd.client(functions.users.GetFullUserRequest(user.id))
    about = full.full_user.about or "—"
    rows = [kv("الاسم", mention(user), "👤"), kv("الايدي", f"`{user.id}`", "🆔"),
            kv("المعرف", f"@{user.username}" if user.username else "لا يوجد", "✨"),
            kv("البايو", about[:100], "📝"), kv("بوت", "نعم" if user.bot else "لا", "🤖")]
    if getattr(user, "premium", False):
        rows.append(kv("بريميوم", "نعم ⭐", "💎"))
    if cmd.in_group:
        try:
            p = await cmd.client.get_permissions(cmd.chat_id, user.id)
            role = "مالك 👑" if p.is_creator else "مشرف 👮" if p.is_admin else "عضو"
            rows.append(kv("الرتبة", role, "🏅"))
        except Exception:
            pass
    await cmd.edit(card("بيانات العضو", rows))


@command(".ر", ".رابط", section="moderation", helpers=True, scope="group", desc="استخراج رابط دعوة المجموعة")
async def invite_link(cmd):
    res = await cmd.client(functions.messages.ExportChatInviteRequest(peer=cmd.chat_id))
    await cmd.edit(f"🔗 **رابط المجموعة:**\n{res.link}")


@command(".تاك_عام", ".تاك", section="moderation", helpers=True, scope="group", usage=".تاك_عام [نص]",
         desc="منشن لكل الأعضاء (دفعات صغيرة)")
async def tag_all(cmd):
    text = cmd.args or "📢 نداء لجميع الأعضاء:"
    await cmd.edit("⏳ جاري جمع الأعضاء...")
    users = [u async for u in cmd.client.iter_participants(cmd.chat_id, limit=2000) if not u.bot and not u.deleted]
    if cmd.is_owner:
        await cmd.delete()
    for i in range(0, len(users), 5):
        chunk = " | ".join(mention(u) for u in users[i:i + 5])
        await cmd.client.send_message(cmd.chat_id, f"{text}\n{chunk}")
        await asyncio.sleep(1.5)


async def _list(cmd, flt, title, icon):
    res = await cmd.client(GetParticipantsRequest(channel=cmd.chat_id, filter=flt, offset=0, limit=100, hash=0))
    cmd.need(res.users, f"لا يوجد {title} بهذي المجموعة.")
    rows = [f"{icon} {mention(u)} — `{u.id}`" for u in res.users]
    await cmd.edit(card(f"{title} ({len(res.users)})", rows))


@command(".المقيدين", section="moderation", helpers=True, scope="group", desc="قائمة المقيدين والمحظورين")
async def banned_list(cmd):
    await _list(cmd, ChannelParticipantsBanned(""), "المقيدين والمحظورين", "🚫")


@command(".المشرفين", section="moderation", helpers=True, scope="group", desc="قائمة مشرفي المجموعة")
async def admins_list(cmd):
    await _list(cmd, ChannelParticipantsAdmins(), "المشرفين", "👮")


@command(".البوتات", section="moderation", helpers=True, scope="group", desc="قائمة بوتات المجموعة")
async def bots_list(cmd):
    await _list(cmd, ChannelParticipantsBots(), "البوتات", "🤖")


@command(".احصائيات", section="moderation", helpers=True, scope="group", desc="إحصائيات المجموعة (أعضاء، مشرفين، بوتات، محذوفين)")
async def stats(cmd):
    await cmd.edit("⏳ **أجمع الإحصائيات...**")
    total = admins = bots = deleted = 0
    async for u in cmd.client.iter_participants(cmd.chat_id, limit=5000):
        total += 1
        bots += bool(u.bot)
        deleted += bool(u.deleted)
    async for _ in cmd.client.iter_participants(cmd.chat_id, filter=ChannelParticipantsAdmins()):
        admins += 1
    chat = await cmd.event.get_chat()
    await cmd.edit(card(f"إحصائيات {getattr(chat, 'title', '')}", [
        kv("الأعضاء", f"`{total}`", "👥"), kv("المشرفين", f"`{admins}`", "👮"),
        kv("البوتات", f"`{bots}`", "🤖"), kv("حسابات محذوفة", f"`{deleted}`", "👻"),
        kv("الايدي", f"`{cmd.chat_id}`", "🆔")], icon="📊"))


@command(".طرد_المحذوفين", section="moderation", scope="group", desc="طرد الحسابات المحذوفة من المجموعة (تحتاج صلاحية)")
async def kick_deleted(cmd):
    await cmd.edit("⏳ **أبحث عن الحسابات المحذوفة...**")
    n = 0
    async for u in cmd.client.iter_participants(cmd.chat_id, limit=5000):
        if u.deleted:
            try:
                await cmd.client.kick_participant(cmd.chat_id, u.id)
                n += 1
                await asyncio.sleep(0.7)
            except Exception:
                pass
    await cmd.edit(f"🧹 تم طرد **{n}** حساب محذوف.")


# ───────────────────────── القفل والفتح
LOCKS = {
    "الاضافه": ("invite_users", "إضافة الأعضاء"), "الاضافة": ("invite_users", "إضافة الأعضاء"),
    "الدردشه": ("send_messages", "الدردشة"), "الدردشة": ("send_messages", "الدردشة"),
    "الصور": ("send_photos", "الصور"), "الفيديو": ("send_videos", "الفيديوهات"),
    "الصوتيات": ("send_audios", "الصوتيات"), "البصمات": ("send_voices", "الرسائل الصوتية"),
    "الملفات": ("send_docs", "الملفات"), "الملصقات": ("send_stickers", "الملصقات"),
    "المتحركات": ("send_gifs", "المتحركات"), "الروابط": ("embed_links", "الروابط"),
    "الاستفتاء": ("send_polls", "الاستفتاءات"), "الميديا": ("send_media", "كل الميديا"),
    "التثبيت": ("pin_messages", "التثبيت"), "المعلومات": ("change_info", "تغيير معلومات المجموعة"),
}


async def _set_lock(cmd, lock):
    what = (cmd.args.split() or [""])[0]
    if what == "التحويل":
        await cmd.client(functions.channels.ToggleNoForwardsRequest(channel=cmd.chat_id, enabled=lock))
        return await cmd.edit("🚫 تم منع التحويل وحفظ المحتوى." if lock else "✅ تم السماح بالتحويل.")
    spec = LOCKS.get(what)
    if not spec:
        names = " - ".join(sorted({k for k in LOCKS if k not in ("الاضافة", "الدردشة")}))
        cmd.fail(f"حدد الشي: `.{'قفل' if lock else 'فتح'} <النوع>`\nالأنواع: {names} - التحويل")
    flag, label = spec
    chat = await cmd.event.get_chat()
    current = getattr(chat, "default_banned_rights", None)
    rights = {n: True for n in _VALID if current is not None and getattr(current, n, False)}
    if lock:
        rights[flag] = True
    else:
        rights.pop(flag, None)
    await cmd.client(functions.messages.EditChatDefaultBannedRightsRequest(
        peer=cmd.chat_id, banned_rights=ChatBannedRights(until_date=None, **rights)))
    await cmd.edit(f"🔒 تم **قفل** {label}." if lock else f"🔓 تم **فتح** {label}.")


@command(".قفل", section="moderation", helpers=True, scope="group", usage=".قفل <الصور|الروابط|الملفات|الدردشه|التحويل ...>",
         desc="قفل صلاحية بالمجموعة (يحافظ على باقي القيود)")
async def lock(cmd):
    await _set_lock(cmd, True)


@command(".فتح", section="moderation", helpers=True, scope="group", usage=".فتح <النوع>", desc="فتح صلاحية مقفولة")
async def unlock(cmd):
    await _set_lock(cmd, False)
