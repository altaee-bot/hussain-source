"""نظام التحذيرات + منع الكلمات."""
import re

from telethon import events

from core.framework import command, listener
from core.ui import card, kv, mention


def _warns(ctx):
    return ctx.state.dict("warns")


@command(".تحذير", section="protection", helpers=True, scope="group", usage=".تحذير [رد/@يوزر] [سبب]",
         desc="تحذير عضو؛ عند بلوغ الحد (افتراضي 3) يُطرد تلقائياً")
async def warn(cmd):
    user = await cmd.target(allow_self=False)
    reason = (cmd.rest or "").strip() or "بدون سبب"
    ctx = cmd.ctx
    chat = _warns(ctx).setdefault(str(cmd.chat_id), {})
    lst = chat.setdefault(str(user.id), [])
    lst.append(reason[:100])
    limit = ctx.state.get("warn_limit", 3)
    ctx.save()
    if len(lst) >= limit:
        chat.pop(str(user.id), None)
        ctx.save()
        await cmd.client.kick_participant(cmd.chat_id, user.id)
        return await cmd.edit(f"🚷 {mention(user)} وصل **{limit}/{limit}** تحذيرات وتم طرده.")
    await cmd.edit(card("تحذير", [kv("العضو", mention(user), "👤"), kv("السبب", reason, "📝"),
                                   kv("التحذيرات", f"`{len(lst)}/{limit}`", "⚠️")], icon="⚠️"))


@command(".التحذيرات", section="protection", helpers=True, scope="group", usage=".التحذيرات [رد/@يوزر]", desc="عرض تحذيرات عضو")
async def warns_list(cmd):
    user = await cmd.target()
    lst = _warns(cmd.ctx).get(str(cmd.chat_id), {}).get(str(user.id), [])
    cmd.need(lst, f"{mention(user)} ما عنده تحذيرات.")
    await cmd.edit(card(f"تحذيرات {user.first_name}", [f"{i}. {r}" for i, r in enumerate(lst, 1)]))


@command(".حذف_التحذيرات", section="protection", helpers=True, scope="group", usage=".حذف_التحذيرات [رد/@يوزر]",
         desc="تصفير تحذيرات عضو")
async def warns_clear(cmd):
    user = await cmd.target()
    _warns(cmd.ctx).get(str(cmd.chat_id), {}).pop(str(user.id), None)
    cmd.ctx.save()
    await cmd.edit(f"✅ تم تصفير تحذيرات {mention(user)}.")


@command(".حد_التحذير", section="protection", usage=".حد_التحذير <رقم>", desc="تغيير عدد التحذيرات قبل الطرد")
async def warn_limit(cmd):
    n = cmd.int_arg(None, 1, 20)
    cmd.need(n, "اكتب رقم من 1 إلى 20.")
    cmd.ctx.state.set("warn_limit", n)
    await cmd.edit(f"✅ صار الحد **{n}** تحذيرات قبل الطرد.")


# ───────────────────────── منع الكلمات
def _words(ctx):
    return ctx.state.dict("banned_words")


@command(".منع", section="protection", helpers=True, scope="group", usage=".منع <كلمة>",
         desc="منع كلمة بالمجموعة (تنحذف الرسائل اللي فيها — تحتاج صلاحية حذف)")
async def ban_word(cmd):
    word = cmd.args.strip().lower()
    cmd.need(word, "اكتب الكلمة بعد الأمر.")
    lst = _words(cmd.ctx).setdefault(str(cmd.chat_id), [])
    cmd.need(word not in lst, "الكلمة ممنوعة بالفعل.")
    lst.append(word)
    cmd.ctx.save()
    await cmd.edit(f"🚫 تم منع الكلمة: `{word}`")


@command(".الغاء_منع", section="protection", helpers=True, scope="group", usage=".الغاء_منع <كلمة>", desc="السماح بكلمة ممنوعة")
async def unban_word(cmd):
    word = cmd.args.strip().lower()
    lst = _words(cmd.ctx).get(str(cmd.chat_id), [])
    cmd.need(word in lst, "الكلمة مو ممنوعة.")
    lst.remove(word)
    cmd.ctx.save()
    await cmd.edit(f"✅ تم السماح بالكلمة: `{word}`")


@command(".قائمة_المنع", section="protection", helpers=True, scope="group", desc="الكلمات الممنوعة بهذي المجموعة")
async def words_list(cmd):
    lst = _words(cmd.ctx).get(str(cmd.chat_id), [])
    cmd.need(lst, "ما في كلمات ممنوعة.")
    await cmd.edit("**🚫 الكلمات الممنوعة:**\n" + "\n".join(f"• `{w}`" for w in lst))


@listener(events.NewMessage(incoming=True))
async def word_filter(event, ctx):
    if not event.is_group or not event.raw_text:
        return
    words = ctx.state.get("banned_words")
    lst = words.get(str(event.chat_id)) if words else None
    if not lst or event.sender_id in ctx.helpers:
        return
    text = event.raw_text.lower()
    if any(re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text) for w in lst):
        await event.delete()
