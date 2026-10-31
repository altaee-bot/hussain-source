"""الذكاء الاصطناعي، صنع كروبات، صنع بوتات."""
import asyncio
import random
import re
from datetime import datetime

from telethon import functions

from core.ai_engines import get_super_ai_response
from core.framework import command
from core.ui import card, kv

WELCOME_MSGS = [
    "✨ **أهلاً وسهلاً بالجميع في رحاب هذا الجروب!**",
    "💎 **هذا الجروب تم إنشاؤه خصيصاً لراحتكم وتواصلكم.**",
    "🎉 **مرحباً بكم في عالمكم الجديد.. نورتونا!**",
    "⚡️ **تم إنشاء هذا الجروب بواسطة سورس ريكو المطور.**",
    "🌟 **بوجودكم تكتمل الفرحة.. أهلاً بكم.**",
    "🚀 **انطلقوا الآن وشاركونا إبداعاتكم.**",
]


@command(".ذكاء", ".ريكو", section="ai", usage=".ذكاء <سؤالك>  (أو بالرد على رسالة)",
         desc="ذكاء اصطناعي: يجرب عدة محركات بنفس الوقت ويرجع أسرع جواب (Gemini لو حطيت المفتاح)")
async def ask(cmd):
    prompt = cmd.args
    r = await cmd.reply_msg()
    if r is not None and r.raw_text:
        prompt = f"{prompt}\n\n{r.raw_text}".strip() if prompt else r.raw_text
    cmd.need(prompt, "اكتب سؤالك بعد الأمر أو رد على رسالة.")
    await cmd.edit("🧠 **ريكو يفكر...**")
    answer = await get_super_ai_response(prompt)
    if not answer:
        cmd.fail("كل المحركات مشغولة أو متوقفة حالياً. جرب بعد شوي، أو ضع `GEMINI_API_KEY` لجواب أضمن.")
    await cmd.edit(f"🤖 **ريكو AI:**\n{answer}")


@command(".صنع", section="ai", usage=".صنع <العدد>", desc="إنشاء سوبر كروبات (حتى 50) وإرسال روابطها لرسائلك المحفوظة")
async def make_groups(cmd):
    count = cmd.int_arg(None, 1, 50)
    cmd.need(count, "حدد العدد (1-50). مثال: `.صنع 5`")
    client = cmd.client
    await cmd.edit(f"⚙️ **بدأت المهمة — إنشاء ({count}) سوبر كروب.** النتائج تجيك بالرسائل المحفوظة.")
    date_now = datetime.now().strftime("%Y/%m/%d")
    for i in range(1, count + 1):
        title = f"كروب {i} - {date_now}"
        try:
            res = await client(functions.channels.CreateChannelRequest(
                title=title, about="تم الإنشاء بواسطة سورس ريكو المطور ⚡️", megagroup=True))
            chat = res.chats[0].id
            for _ in range(3):
                await client.send_message(chat, random.choice(WELCOME_MSGS))
                await asyncio.sleep(0.4)
            link = await client(functions.messages.ExportChatInviteRequest(peer=chat))
            await client.send_message("me", card(f"تم إنشاء كروب {i}/{count}", [
                kv("الاسم", title, "📦"), kv("الرابط", link.link, "🔗")], icon="👑"))
            if i < count:
                await asyncio.sleep(30)
        except Exception as e:
            await client.send_message("me", f"❌ **توقفت العملية عند الكروب {i}:**\n`{str(e)[:150]}`")
            return
    await client.send_message("me", "🏁 **اكتملت عملية إنشاء الكروبات.**")


@command(".بوت", section="ai", usage=".بوت <الاسم> <اليوزر>", desc="صنع بوت عبر @BotFather (التوكن يوصل لرسائلك المحفوظة فقط)")
async def make_bot(cmd):
    parts = cmd.args.split()
    cmd.need(len(parts) >= 2, "الصيغة: `.بوت ريكو reco_bot`")
    name, username = " ".join(parts[:-1]), parts[-1].lstrip("@")
    cmd.need(username.lower().endswith("bot"), "يوزر البوت لازم ينتهي بكلمة `bot`.")
    await cmd.edit(f"⏳ **جاري إنشاء البوت عبر BotFather...**\n🏷 `{name}`  👤 `@{username}`")
    async with cmd.client.conversation("@BotFather", timeout=60) as conv:
        await conv.send_message("/newbot")
        await conv.get_response()
        await conv.send_message(name)
        resp = await conv.get_response()
        if "sorry" in (resp.text or "").lower():
            cmd.fail("رفض BotFather الاسم، جرب اسم ثاني.")
        await conv.send_message(username)
        resp = await conv.get_response()
        txt = resp.text or ""
        if "already taken" in txt.lower():
            cmd.fail("هذا اليوزر محجوز، جرب غيره.")
        if "Done!" not in txt:
            cmd.fail(f"رفض BotFather الطلب:\n{txt[:150]}")
    token = (re.search(r"\d+:[A-Za-z0-9_-]{30,}", txt) or [None])[0] or "لم أجد التوكن — راجع محادثة BotFather"
    await cmd.client.send_message("me", card("بوتك الجديد", [
        kv("الاسم", f"`{name}`", "📦"), kv("اليوزر", f"@{username}", "👤"),
        kv("التوكن", f"`{token}`", "🔑"), kv("الوقت", datetime.now().strftime("%Y-%m-%d %H:%M"), "📅")], icon="🤖"))
    await cmd.edit(f"✅ **تم إنشاء @{username}!**\n🔒 التوكن أُرسل لرسائلك المحفوظة فقط (حفاظاً على سريته).")
