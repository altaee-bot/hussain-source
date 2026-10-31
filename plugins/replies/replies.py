"""الردود التلقائية + الترحيب والتوديع + التشويش."""
from telethon import events, types

from core.framework import command, listener
from core.ui import card


def _key(text):
    return " ".join((text or "").split()).casefold()


# ───────────────────────── الردود
@command(".رد", section="replies", usage=".رد كلمة | جواب   أو   (بالرد على كلمة) .رد",
         desc="إضافة رد تلقائي. الطريقة السريعة: `.رد سلام | وعليكم السلام`")
async def add_reply(cmd):
    ctx = cmd.ctx
    if "|" in cmd.args:
        word, _, answer = cmd.args.partition("|")
        word, answer = word.strip(), answer.strip()
        cmd.need(word and answer, "الصيغة: `.رد كلمة | الجواب`")
        ctx.responses[_key(word)] = {"word": word, "answer": answer}
        ctx.save_responses()
        return await cmd.edit(card("تم حفظ الرد", [f"🔹 **الكلمة:** `{word}`", f"🔸 **الجواب:** `{answer}`"], icon="✅"))
    r = await cmd.reply_msg()
    cmd.need(r and r.raw_text, "رد على الكلمة، أو اكتب: `.رد كلمة | الجواب`")
    ctx.reply_state[cmd.event.sender_id] = r.raw_text
    await cmd.edit(f"⏳ **الكلمة:** `{r.raw_text}`\n💬 **أرسل الآن الجواب لحفظه.**")


@listener(events.NewMessage(outgoing=True))
async def capture_answer(event, ctx):
    """الخطوة الثانية من .رد: أول رسالة عادية تكتبها = الجواب."""
    uid = event.sender_id
    text = event.raw_text
    if uid not in ctx.reply_state or not text or text.startswith(".رد"):
        return
    word = ctx.reply_state.pop(uid)
    ctx.responses[_key(word)] = {"word": word, "answer": text}
    ctx.save_responses()
    await event.edit(card("تم حفظ الرد", [f"🔹 **الكلمة:** `{word}`", f"🔸 **الجواب:** `{text}`"], icon="✅"))


@command(".حذف_رد", section="replies", usage=".حذف_رد <كلمة>  أو بالرد على الكلمة", desc="حذف رد")
async def del_reply(cmd):
    r = await cmd.reply_msg()
    word = cmd.args or (r.raw_text if r else "")
    cmd.need(word, "اكتب الكلمة أو رد عليها.")
    k = _key(word)
    cmd.need(k in cmd.ctx.responses, "هذي الكلمة ما عليها رد.")
    del cmd.ctx.responses[k]
    cmd.ctx.save_responses()
    await cmd.edit(f"🗑 تم حذف الرد الخاص بـ `{word}`")


@command(".ردودي", section="replies", desc="عرض كل الردود المحفوظة")
async def list_replies(cmd):
    cmd.need(cmd.ctx.responses, "📭 ما عندك ردود محفوظة.")
    rows = []
    for v in cmd.ctx.responses.values():
        w, a = (v["word"], v["answer"]) if isinstance(v, dict) else ("?", str(v))
        rows.append(f"🔹 `{w}` ⬅️ `{a[:60]}`")
    await cmd.edit(card(f"ردودك ({len(rows)})", rows))


@command(".ردود_الكروبات", section="replies", usage=".ردود_الكروبات تشغيل|ايقاف",
         desc="تشغيل/إيقاف الردود التلقائية داخل المجموعات (بالخاص تبقى شغالة)")
async def replies_groups(cmd):
    w = cmd.words[:1]
    on = not (w and w[0] in ("ايقاف", "تعطيل", "off"))
    cmd.ctx.state.set("replies_groups", on)
    await cmd.edit("✅ الردود بالمجموعات: **شغالة**" if on else "⛔ الردود بالمجموعات: **متوقفة**")


@listener(events.NewMessage(incoming=True))
async def auto_reply(event, ctx):
    if not ctx.responses or not event.raw_text:
        return
    hit = ctx.responses.get(_key(event.raw_text))
    if hit is None:
        return
    if not event.is_private and not ctx.state.get("replies_groups", True):
        return
    sender = await event.get_sender()
    if getattr(sender, "bot", False):
        return
    if not ctx.cooldown(("rep", event.chat_id, _key(event.raw_text)), 5):
        return
    await event.reply(hit["answer"] if isinstance(hit, dict) else str(hit))


@command(".تشويش", section="replies", usage=".تشويش <نص>", desc="إرسال نص مخفي (سبويلر)")
async def spoiler(cmd):
    cmd.need(cmd.args, "اكتب النص بعد الأمر.")
    await cmd.event.edit(cmd.args, formatting_entities=[types.MessageEntitySpoiler(offset=0, length=len(cmd.args))])


# ───────────────────────── الترحيب والتوديع
DEFAULT_WELCOME = "اهلا بك يا {mention} في {chat}! نورتنا ✨"
DEFAULT_BYE = "{name} غادر.. سد الباب وراك، لا يجينا الهوى! 🚪👋"


def _toggle(key):
    async def run(cmd, on):
        cmd.ctx.state.set(key, on)
    return run


@command(".تفعيل_ترحيب", section="replies", helpers=True, desc="تشغيل الترحيب التلقائي بالأعضاء الجدد")
async def welcome_on(cmd):
    cmd.ctx.state.set("welcome", True)
    await cmd.edit("✅ تم **تشغيل** الترحيب التلقائي.")


@command(".تعطيل_ترحيب", section="replies", helpers=True, desc="إيقاف الترحيب")
async def welcome_off(cmd):
    cmd.ctx.state.set("welcome", False)
    await cmd.edit("⛔ تم **إيقاف** الترحيب.")


@command(".تفعيل_توديع", section="replies", helpers=True, desc="تشغيل التوديع التلقائي عند المغادرة")
async def bye_on(cmd):
    cmd.ctx.state.set("goodbye", True)
    await cmd.edit("✅ تم **تشغيل** التوديع التلقائي.")


@command(".تعطيل_توديع", section="replies", helpers=True, desc="إيقاف التوديع")
async def bye_off(cmd):
    cmd.ctx.state.set("goodbye", False)
    await cmd.edit("⛔ تم **إيقاف** التوديع.")


@command(".ترحيب", section="replies", helpers=True, usage=".ترحيب <النص>",
         desc="تغيير نص الترحيب. المتغيرات: `{mention}` `{name}` `{chat}` — و `.ترحيب افتراضي` للرجوع")
async def set_welcome(cmd):
    cmd.need(cmd.args, "اكتب نص الترحيب. مثال: `.ترحيب هلا {mention} بـ {chat} 🌹`")
    if cmd.args.strip() in ("افتراضي", "default"):
        cmd.ctx.state.data.pop("welcome_text", None)
        cmd.ctx.save()
        return await cmd.edit("✅ رجعنا لنص الترحيب الافتراضي.")
    cmd.ctx.state.set("welcome_text", cmd.args)
    await cmd.edit("✅ تم حفظ نص الترحيب. لازم الترحيب يكون مشغّل: `.تفعيل_ترحيب`")


@command(".توديع", section="replies", helpers=True, usage=".توديع <النص>", desc="تغيير نص التوديع (نفس المتغيرات)")
async def set_bye(cmd):
    cmd.need(cmd.args, "اكتب نص التوديع.")
    if cmd.args.strip() in ("افتراضي", "default"):
        cmd.ctx.state.data.pop("goodbye_text", None)
        cmd.ctx.save()
        return await cmd.edit("✅ رجعنا لنص التوديع الافتراضي.")
    cmd.ctx.state.set("goodbye_text", cmd.args)
    await cmd.edit("✅ تم حفظ نص التوديع.")


def _fmt(template, user, chat):
    name = (getattr(user, "first_name", "") or "عضو")
    return template.format(mention=f"[{name}](tg://user?id={user.id})", name=name,
                           chat=getattr(chat, "title", "المجموعة"), id=user.id)


@listener(events.ChatAction)
async def greet(event, ctx):
    joined = event.user_joined or event.user_added
    left = event.user_left or event.user_kicked
    if not (joined or left):
        return
    on = ctx.state.get("welcome", False) if joined else ctx.state.get("goodbye", False)
    if not on or not ctx.cooldown(("greet", event.chat_id, joined), 2):
        return
    user = await event.get_user()
    if user is None or getattr(user, "bot", False):
        return
    chat = await event.get_chat()
    tpl = ctx.state.get("welcome_text", DEFAULT_WELCOME) if joined else ctx.state.get("goodbye_text", DEFAULT_BYE)
    try:
        await event.reply(_fmt(tpl, user, chat))
    except (KeyError, IndexError):
        await event.reply(tpl)
