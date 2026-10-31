"""المساعدين (يقدرون ينفذون أوامر الإدارة نيابة عنك) + الحظر العام + حذف رسائل المكتومين."""
from telethon import events, functions

from core.framework import command, listener
from core.ui import mention


@command(".رفع_مساعد", section="protection", usage=".رفع_مساعد [رد/@يوزر]",
         desc="رفع مساعد: ينفذ أوامر الإدارة (حظر، كتم، قفل...) نيابة عنك")
async def add_helper(cmd):
    user = await cmd.target(allow_self=False)
    cmd.need(not user.bot, "ما يصير ترفع بوت مساعد.")
    cmd.need(user.id not in cmd.ctx.helpers, "هذا المستخدم مساعد بالفعل.")
    cmd.ctx.helpers.append(user.id)
    cmd.ctx.save()
    await cmd.edit(f"✅ تم رفع {mention(user)} كمساعد بالسورس.")


@command(".تنزيل_مساعد", section="protection", usage=".تنزيل_مساعد [رد/@يوزر]", desc="تنزيل مساعد وسحب صلاحياته")
async def del_helper(cmd):
    user = await cmd.target()
    cmd.need(user.id in cmd.ctx.helpers, "هذا المستخدم مو مساعد.")
    cmd.ctx.helpers.remove(user.id)
    cmd.ctx.save()
    await cmd.edit(f"✅ تم تنزيل {mention(user)} وسحب صلاحياته.")


@command(".المساعدين", section="protection", desc="عرض قائمة المساعدين")
async def helpers_list(cmd):
    cmd.need(cmd.ctx.helpers, "ما عندك مساعدين.")
    await cmd.edit("**👥 المساعدين:**\n" + "\n".join(f"• [{i}](tg://user?id={i})" for i in cmd.ctx.helpers))


@command(".حظر_عام", section="protection", usage=".حظر_عام [رد/@يوزر]",
         desc="بلوك بالخاص + طرد الشخص من كل المجموعات اللي أنت أدمن فيها")
async def global_ban(cmd):
    user = await cmd.target(allow_self=False)
    await cmd.edit("⏳ **جاري تنفيذ الحظر العام...**")
    await cmd.client(functions.contacts.BlockRequest(id=user.id))
    count = 0
    async for d in cmd.client.iter_dialogs():
        if not (d.is_group or d.is_channel):
            continue
        ent = d.entity
        if not (getattr(ent, "creator", False) or getattr(ent, "admin_rights", None)):
            continue
        try:
            await cmd.client.edit_permissions(d.id, user.id, view_messages=False)
            count += 1
        except Exception:
            continue
    await cmd.edit(f"🚫 **تم الحظر العام لـ {mention(user)}**\n🔒 بلوك خاص + حظر من **{count}** مجموعة/قناة.")


@command(".الغاء_عام", section="protection", usage=".الغاء_عام [رد/@يوزر]", desc="فك البلوك الخاص (الكروبات تُفك يدوياً)")
async def global_unban(cmd):
    user = await cmd.target()
    await cmd.client(functions.contacts.UnblockRequest(id=user.id))
    await cmd.edit(f"✅ تم فك البلوك عن {mention(user)}.")


@listener(events.NewMessage(incoming=True))
async def delete_muted(event, ctx):
    muted = ctx.state.get("muted")
    if not muted or event.sender_id not in muted:
        return
    if event.is_private:
        return await event.delete()
    if event.is_group:
        is_admin = ctx.cached(("adm", event.chat_id), 300)
        if is_admin is None:
            me = await ctx.get_me()
            perms = await ctx.client.get_permissions(event.chat_id, me.id)
            is_admin = ctx.put_cache(("adm", event.chat_id), bool(perms.is_admin or perms.is_creator))
        if is_admin:
            await event.delete()
