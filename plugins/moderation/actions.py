"""حظر، طرد، كتم، تقييد، رفع/تنزيل أدمن، تثبيت، مسح — كلها تقبل (رد / @يوزر / ايدي)."""
import asyncio
import re
from datetime import datetime, timedelta, timezone

from telethon import functions
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights

from core.framework import CmdError, command
from core.ui import mention

_UNITS = {"د": 60, "m": 60, "min": 60, "س": 3600, "h": 3600, "hr": 3600, "ي": 86400, "d": 86400}


def parse_duration(text, default_unit=3600):
    """'30m' '2h' '1d' '3س' '45د' أو رقم فقط (= ساعات). يرجع ثواني أو None."""
    m = re.fullmatch(r"(\d+)\s*([a-zA-Zدسي]*)", (text or "").strip())
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2).lower()
    if unit and unit not in _UNITS:
        return None
    return n * (_UNITS[unit] if unit else default_unit)


def fmt_duration(sec):
    d, r = divmod(int(sec), 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    return " و".join(x for x in (f"{d} يوم" if d else "", f"{h} ساعة" if h else "", f"{m} دقيقة" if m else "") if x) or "أقل من دقيقة"


async def _need_group(cmd):
    cmd.need(cmd.in_group, "هذا الأمر يعمل داخل المجموعات والقنوات فقط.")


@command(".حظر", section="moderation", helpers=True, usage=".حظر [رد/@يوزر]",
         desc="بالمجموعة: حظر نهائي من المجموعة. بالخاص: بلوك للشخص")
async def ban(cmd):
    user = await cmd.target(allow_self=False)
    if cmd.in_group:
        await cmd.client(EditBannedRequest(cmd.chat_id, user.id, ChatBannedRights(until_date=None, view_messages=True)))
        return await cmd.edit(f"🚫 تم حظر {mention(user)} نهائياً من المجموعة.")
    cmd.need(cmd.is_owner, "البلوك للمالك فقط.")
    await cmd.client(functions.contacts.BlockRequest(id=user.id))
    await cmd.edit(f"🚫 تم عمل بلوك لـ {mention(user)} (`{user.id}`).")


@command(".الغاء_حظر", ".الغاء", section="moderation", helpers=True, usage=".الغاء [رد/@يوزر]",
         desc="فك الحظر/الكتم/التقييد عن شخص (بالمجموعة)، أو فك البلوك بالخاص")
async def unban(cmd):
    user = await cmd.target()
    if cmd.in_group:
        await cmd.client(EditBannedRequest(cmd.chat_id, user.id, ChatBannedRights(until_date=None)))
        if user.id in cmd.ctx.muted_users and cmd.is_owner:
            cmd.ctx.muted_users.remove(user.id)
            cmd.ctx.save()
        return await cmd.edit(f"✅ تم إلغاء كل القيود عن {mention(user)}.")
    cmd.need(cmd.is_owner, "هذا للمالك فقط.")
    await cmd.client(functions.contacts.UnblockRequest(id=user.id))
    await cmd.edit(f"✅ تم فك البلوك عن {mention(user)}.")


@command(".طرد", section="moderation", helpers=True, scope="group", usage=".طرد [رد/@يوزر]",
         desc="طرد عضو من المجموعة (يقدر يرجع بالرابط)")
async def kick(cmd):
    user = await cmd.target(allow_self=False)
    await cmd.client.kick_participant(cmd.chat_id, user.id)
    await cmd.edit(f"🚷 تم طرد {mention(user)} من المجموعة.")


@command(".كتم", section="moderation", helpers=True, usage=".كتم [رد/@يوزر]",
         desc="كتم شخص: تنحذف رسائله تلقائياً (وبالمجموعة يتقيّد من الإرسال)")
async def mute(cmd):
    user = await cmd.target(allow_self=False)
    ctx = cmd.ctx
    note = []
    if cmd.is_owner and user.id not in ctx.muted_users:
        ctx.muted_users.append(user.id)
        ctx.save()
        note.append("حذف رسائله تلقائياً")
    if cmd.in_group:
        try:
            await cmd.client(EditBannedRequest(cmd.chat_id, user.id, ChatBannedRights(until_date=None, send_messages=True)))
            note.append("تقييده من الإرسال")
        except Exception:
            pass
    cmd.need(note, "هذا الشخص مكتوم بالفعل.")
    await cmd.edit(f"🔇 تم كتم {mention(user)} — " + " و".join(note) + ".")


@command(".الغاء_كتم", ".فك_كتم", section="moderation", helpers=True, usage=".الغاء_كتم [رد/@يوزر]", desc="إلغاء الكتم")
async def unmute(cmd):
    user = await cmd.target()
    ctx, done = cmd.ctx, False
    if cmd.is_owner and user.id in ctx.muted_users:
        ctx.muted_users.remove(user.id)
        ctx.save()
        done = True
    if cmd.in_group:
        try:
            await cmd.client(EditBannedRequest(cmd.chat_id, user.id, ChatBannedRights(until_date=None)))
            done = True
        except Exception:
            pass
    cmd.need(done, "هذا الشخص مو مكتوم.")
    await cmd.edit(f"🔊 تم إلغاء كتم {mention(user)}.")


@command(".المكتومين", section="moderation", desc="عرض قائمة المكتومين عندك")
async def muted_list(cmd):
    ids = cmd.ctx.muted_users
    cmd.need(ids, "ما عندك مكتومين.")
    await cmd.edit("**🔇 المكتومين:**\n" + "\n".join(f"• [{i}](tg://user?id={i})" for i in ids))


@command(".تقييد", ".تقييد_مؤقت", section="moderation", helpers=True, scope="group",
         usage=".تقييد <مدة> [رد/@يوزر]", desc="كتم مؤقت. المدة: `2` ساعتين، `30m` دقيقة، `1d` يوم، `3س`")
async def restrict(cmd):
    words = cmd.words
    dur_txt = next((w for w in words if parse_duration(w) is not None), None)
    cmd.need(dur_txt, "حدد المدة: `.تقييد 2` (ساعتين) أو `30m` أو `1d`")
    secs = parse_duration(dur_txt)
    cmd.need(60 <= secs <= 366 * 86400, "المدة لازم بين دقيقة وسنة.")
    cmd.args = " ".join(w for w in words if w != dur_txt)
    user = await cmd.target(allow_self=False)
    until = datetime.now(timezone.utc) + timedelta(seconds=secs)
    await cmd.client(EditBannedRequest(cmd.chat_id, user.id, ChatBannedRights(until_date=until, send_messages=True)))
    await cmd.edit(f"⏳ تم تقييد {mention(user)} لمدة **{fmt_duration(secs)}**.")


@command(".حظر_مؤقت", section="moderation", helpers=True, scope="group",
         usage=".حظر_مؤقت <مدة> [رد/@يوزر]", desc="حظر مؤقت من المجموعة ثم يُفك تلقائياً")
async def temp_ban(cmd):
    words = cmd.words
    dur_txt = next((w for w in words if parse_duration(w) is not None), None)
    cmd.need(dur_txt, "حدد المدة: `.حظر_مؤقت 1d`")
    secs = parse_duration(dur_txt)
    cmd.args = " ".join(w for w in words if w != dur_txt)
    user = await cmd.target(allow_self=False)
    until = datetime.now(timezone.utc) + timedelta(seconds=secs)
    await cmd.client(EditBannedRequest(cmd.chat_id, user.id, ChatBannedRights(until_date=until, view_messages=True)))
    await cmd.edit(f"🚫 تم حظر {mention(user)} لمدة **{fmt_duration(secs)}**.")


# ───────────────────────── الإشراف
@command(".ادمن", ".رفع_مشرف", section="moderation", scope="group", usage=".ادمن [رد/@يوزر] [لقب]",
         desc="رفع الشخص مشرف بصلاحيات أساسية (حذف، حظر، دعوة، تثبيت)")
async def promote(cmd):
    user = await cmd.target(allow_self=False)
    title = (cmd.rest or "").strip()[:16] or None
    await cmd.client.edit_admin(cmd.chat_id, user.id, change_info=False, delete_messages=True, ban_users=True,
                                invite_users=True, pin_messages=True, manage_call=True, title=title)
    await cmd.edit(f"👮 تم رفع {mention(user)} مشرف" + (f" بلقب **{title}**." if title else "."))


@command(".تنزيل", ".تنزيل_مشرف", section="moderation", scope="group", usage=".تنزيل [رد/@يوزر]",
         desc="تنزيل مشرف إلى عضو عادي")
async def demote(cmd):
    user = await cmd.target(allow_self=False)
    await cmd.client.edit_admin(cmd.chat_id, user.id, is_admin=False)
    await cmd.edit(f"⬇️ تم تنزيل {mention(user)} من الإشراف.")


@command(".تثبيت", section="moderation", helpers=True, usage=".تثبيت (بالرد)", desc="تثبيت رسالة (بالرد). مع يوزر = تثبيت يوزر للصيد")
async def pin(cmd):
    if cmd.args:   # `.تثبيت <يوزر>` = تثبيت يوزر للصيد (قسم الصيد)
        from plugins.hunting.tools import start_fixed
        return await start_fixed(cmd)
    r = await cmd.reply_msg()
    cmd.need(r, "رد على الرسالة اللي تريد تثبيتها.")
    await cmd.client.pin_message(cmd.chat_id, r.id)
    await cmd.edit("📌 تم تثبيت الرسالة.")


@command(".الغاء_تثبيت", ".الغاء التثبيت", section="moderation", helpers=True, usage=".الغاء_تثبيت [بالرد]",
         desc="إلغاء تثبيت رسالة (بالرد) أو كل المثبتات")
async def unpin(cmd):
    r = await cmd.reply_msg()
    await cmd.client.unpin_message(cmd.chat_id, r.id if r else None)
    await cmd.edit("📍 تم إلغاء التثبيت." if r else "📍 تم إلغاء كل التثبيتات.")


# ───────────────────────── التنظيف
@command(".مسح", section="moderation", helpers=True, usage=".مسح (بالرد)",
         desc="بالرد: يحذف كل الرسائل من المردود عليها حتى الآن. بالخاص بدون رد: مسح المحادثة من الطرفين")
async def clear(cmd):
    ev = cmd.event
    r = await cmd.reply_msg()
    if r is not None:
        ids = [m.id async for m in cmd.client.iter_messages(cmd.chat_id, min_id=r.id - 1)]
        await cmd.client.delete_messages(cmd.chat_id, ids)
        if cmd.is_owner:
            return
        return await cmd.edit(f"🧹 تم حذف {len(ids)} رسالة.")
    cmd.need(cmd.is_owner, "رد على رسالة لبدء الحذف منها.")
    if ev.is_private:
        await cmd.edit("🗑 **جاري مسح المحادثة من الطرفين...**")
        await cmd.client(functions.messages.DeleteHistoryRequest(peer=cmd.chat_id, max_id=0, just_clear=False, revoke=True))
        return
    raise CmdError("بالمجموعات: رد على أول رسالة تريد الحذف منها، أو استعمل `.حذف_رسائلي 20`.\n🚪 للمغادرة: `.مغادرة`")


@command(".حذف_رسائلي", ".مسح_رسائلي", section="moderation", usage=".حذف_رسائلي [العدد]",
         desc="حذف آخر رسائلك بالدردشة (افتراضي 10، أقصى 200)")
async def del_mine(cmd):
    n = cmd.int_arg(10, 1, 200)
    ids = [m.id async for m in cmd.client.iter_messages(cmd.chat_id, from_user="me", limit=n + 1)]
    await cmd.client.delete_messages(cmd.chat_id, ids)


@command(".مغادرة", section="moderation", scope="group", desc="مغادرة هذي المجموعة/القناة مع رسالة وداع")
async def leave(cmd):
    await cmd.edit("🤍 **شكراً لكم على كل شي، أتمنى لكم التوفيق. وداعاً!**")
    await asyncio.sleep(2)
    await cmd.client(functions.channels.LeaveChannelRequest(channel=cmd.chat_id))
