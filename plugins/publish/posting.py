"""التكرار السريع + النشر التلقائي بمجموعة واحدة أو عدة مجموعات (مع معالج خطوات)."""
import asyncio
from datetime import datetime

from telethon import errors, events

from core.framework import command, listener
from core.ui import card, kv

MIN_DELAY = 300
MAX_DELAY = 3000


async def _send_loop(client, target, count, delay, text, on_sent=None, max_fail=5):
    """يرسل `count` رسالة بفاصل `delay`؛ يتحمل FloodWait ويتوقف بعد فشل متكرر (مثلاً انحظرت)."""
    sent = fails = 0
    while sent < count:
        try:
            await client.send_message(target, text)
            sent += 1
            fails = 0
            if on_sent:
                on_sent(sent)
        except errors.FloodWaitError as e:
            await asyncio.sleep(min(e.seconds + 1, 3600))
            continue
        except asyncio.CancelledError:
            raise
        except Exception:
            fails += 1
            if fails >= max_fail:
                return sent, "توقف بسبب أخطاء متكررة (ربما محظور أو بدون صلاحية)"
        if sent < count:
            await asyncio.sleep(delay)
    return sent, None


@command(".كرر", section="publish", usage=".كرر <العدد> <النص>", desc="تكرار رسالة بسرعة (أقصى 500) مع حماية من الفلود")
async def repeat(cmd):
    parts = cmd.args.split(None, 1)
    cmd.need(len(parts) == 2 and parts[0].isdigit(), "الصيغة: `.كرر 5 مرحبا`")
    count, text = int(parts[0]), parts[1]
    cmd.need(1 <= count <= 500, "العدد من 1 إلى 500.")
    await cmd.delete()
    for _ in range(count):
        try:
            await cmd.client.send_message(cmd.chat_id, text)
        except errors.FloodWaitError as e:
            await asyncio.sleep(e.seconds + 1)
            continue
        await asyncio.sleep(0.05)


@command(".تلقائي", section="publish", usage=".تلقائي <رابط/يوزر> <العدد> <الثواني> <النص>",
         desc="نشر مبرمج بمجموعة (أقل فاصل 300 ثانية). داخل الرسائل المحفوظة يكون سري")
async def auto_post(cmd):
    parts = cmd.args.split(None, 3)
    cmd.need(len(parts) == 4 and parts[1].isdigit() and parts[2].isdigit(),
             "الصيغة: `.تلقائي [الرابط] [العدد] [الثواني] [النص]`")
    link, count, seconds, text = parts[0], int(parts[1]), int(parts[2]), parts[3]
    cmd.need(seconds >= MIN_DELAY, f"أقل فاصل **{MIN_DELAY}** ثانية لتجنب حظر حسابك.")
    cmd.need(1 <= count <= 1000, "العدد من 1 إلى 1000.")
    await cmd.edit("⏳ **أفحص الهدف...**")
    ent = await cmd.client.get_entity(link)
    ctx, me = cmd.ctx, await cmd.ctx.get_me()
    if ent.id in ctx.auto_tasks:
        ctx.auto_tasks[ent.id].cancel()
    title = getattr(ent, "title", link)
    if cmd.chat_id == me.id:
        await cmd.edit(card("تم تفعيل النشر السري", [kv("الهدف", title, "🚀"), kv("العدد", f"{count} رسالة", "🔢"),
                                                    kv("الفاصل", f"{seconds} ثانية", "⏱")], icon="🕵️"))
    else:
        await cmd.edit("✅ **تم بدء النشر التلقائي.**")

    async def job():
        try:
            sent, why = await _send_loop(cmd.client, ent, count, seconds, text)
            if why:
                await cmd.client.send_message("me", f"⚠️ نشر `{title}`: أُرسل {sent}/{count} — {why}")
        finally:
            ctx.auto_tasks.pop(ent.id, None)

    ctx.auto_tasks[ent.id] = asyncio.create_task(job())


@command(".ايقاف التلقائي", ".ايقاف_التلقائي", ".ايقاف النشر", section="publish",
         desc="إيقاف النشر: بالمجموعة = هذي المجموعة، وبالرسائل المحفوظة = الكل")
async def stop_auto(cmd):
    ctx, me = cmd.ctx, await cmd.ctx.get_me()
    if cmd.chat_id == me.id:
        n = len(ctx.auto_tasks)
        for t in list(ctx.auto_tasks.values()):
            t.cancel()
        ctx.auto_tasks.clear()
        return await cmd.edit(f"🛑 **تم إيقاف {n} عملية نشر.**" if n else "⚠️ ما في نشر نشط.")
    t = ctx.auto_tasks.pop(cmd.chat_id, None)
    if t:
        t.cancel()
        return await cmd.edit("🛑 **تم إيقاف النشر بهذي الدردشة.**")
    await cmd.edit("⚠️ ما في نشر نشط هنا.")


@command(".حالة النشر", ".حالة_النشر", section="publish", desc="عرض عمليات النشر التلقائي الشغالة")
async def auto_status(cmd):
    cmd.need(cmd.ctx.auto_tasks, "📭 ما في عمليات نشر شغالة.")
    await cmd.edit(card("النشر الجاري", [f"• `{k}`" for k in cmd.ctx.auto_tasks], icon="📊"))


# ───────────────────────── النشر بعدة مجموعات (معالج)
def _gp(ctx):
    return ctx.group_publish


async def _start_group_tasks(cmd_or_ctx, client, ctx, links, message, delay, count):
    gp = _gp(ctx)
    errs = []
    for link in links:
        try:
            ent = await client.get_entity(link)
        except Exception as e:
            errs.append(f"❌ {link}: {str(e)[:60]}")
            continue

        def mark(n, link=link):
            gp["sent"][link] = n
            gp["last_sent"][link] = datetime.now()

        async def job(ent=ent, link=link, mark=mark):
            try:
                await _send_loop(client, ent, count, delay, message, on_sent=mark)
            finally:
                gp["tasks"].pop(link, None)

        old = gp["tasks"].pop(link, None)
        if old:
            old.cancel()
        gp["tasks"][link] = asyncio.create_task(job())
    return errs


@command(".اضف_مجموعة", section="publish", desc="معالج خطوات: أضف روابط (حتى 10) ← كليشة ← فاصل ← عدد، ويبدأ النشر")
async def add_groups(cmd):
    cmd.ctx.add_group_data[cmd.event.sender_id] = {"links": [], "step": "links", "message": None, "delay": None}
    await cmd.edit("✅ **بدأ معالج إضافة المجموعات.**\n📬 أرسل الروابط/اليوزرات واحد واحد (حتى 10).\n✍️ وعند الانتهاء أرسل: `تم`\n❌ للإلغاء: `الغاء`")


@listener(events.NewMessage(outgoing=True))
async def add_groups_wizard(event, ctx):
    uid = event.sender_id
    data = ctx.add_group_data.get(uid)
    text = (event.raw_text or "").strip()
    if not data or not text or text.startswith(".اضف_مجموعة"):
        return
    if text in ("الغاء", "إلغاء"):
        ctx.add_group_data.pop(uid, None)
        return await event.edit("❌ **تم إلغاء المعالج.**")
    step = data["step"]
    if step == "links":
        if text == "تم":
            if not data["links"]:
                ctx.add_group_data.pop(uid, None)
                return await event.edit("❌ لم تضف أي روابط — تم الإلغاء.")
            data["step"] = "message"
            return await event.edit("📄 **الآن أرسل الكليشة (نص الرسالة):**")
        if len(data["links"]) >= 10:
            return await event.edit("⚠️ وصلت الحد (10). أرسل `تم` للمتابعة.")
        try:
            await ctx.client.get_entity(text)
        except Exception as e:
            return await event.edit(f"❌ **رابط غير صالح:** `{str(e)[:80]}`\nجرب ثانية أو أرسل `تم`.")
        data["links"].append(text)
        await event.edit(f"✅ **تمت إضافة الرابط {len(data['links'])}.** أرسل التالي أو `تم`.")
    elif step == "message":
        data["message"] = text
        data["step"] = "delay"
        await event.edit(f"⏱ **أرسل الفاصل بالثواني ({MIN_DELAY} إلى {MAX_DELAY}):**")
    elif step == "delay":
        if not text.isdigit() or not MIN_DELAY <= int(text) <= MAX_DELAY:
            return await event.edit(f"⚠️ رقم من {MIN_DELAY} إلى {MAX_DELAY}.")
        data["delay"] = int(text)
        data["step"] = "count"
        await event.edit("🔢 **أرسل عدد الرسائل لكل مجموعة:**")
    elif step == "count":
        if not text.isdigit() or not 1 <= int(text) <= 1000:
            return await event.edit("⚠️ رقم من 1 إلى 1000.")
        gp = _gp(ctx)
        gp.update(links=data["links"], message=data["message"], delay=data["delay"], count=int(text),
                  sent={l: 0 for l in data["links"]}, last_sent={})
        ctx.add_group_data.pop(uid, None)
        await event.edit("🚀 **جاري بدء النشر...**")
        errs = await _start_group_tasks(None, ctx.client, ctx, list(data["links"]), data["message"], data["delay"], int(text))
        await event.edit("✅ **بدأ النشر بكل المجموعات.**" + ("\n" + "\n".join(errs) if errs else ""))


@command(".ايقاف_مجموعة", section="publish", desc="إيقاف النشر بكل المجموعات")
async def stop_groups(cmd):
    gp = _gp(cmd.ctx)
    for t in gp["tasks"].values():
        t.cancel()
    gp["tasks"].clear()
    await cmd.edit("🛑 **تم إيقاف النشر بكل المجموعات.**")


@command(".حالة_المجموعة", section="publish", desc="تقرير حالة النشر بالمجموعات")
async def groups_status(cmd):
    gp = _gp(cmd.ctx)
    cmd.need(gp["links"], "📭 ما في مجموعات نشر.")
    rows, total = [], 0
    for link in gp["links"]:
        sent = gp["sent"].get(link, 0)
        total += sent
        state = "نشط ✅" if link in gp["tasks"] else "مكتمل/متوقف 🛑"
        rows.append(f"🔹 `{link}`\n   ├ المرسل: `{sent}/{gp['count']}`\n   └ الحالة: {state}")
    rows.append(f"📈 **الإجمالي:** `{total}`  |  📋 **المجموعات:** `{len(gp['links'])}`")
    await cmd.edit(card("حالة النشر بالمجموعات", rows, icon="📊"))


@command(".تعديل_مجموعة", section="publish", usage=".تعديل_مجموعة <رابط>", desc="إضافة رابط جديد لقائمة النشر وبدء النشر فيه")
async def edit_group(cmd):
    gp = _gp(cmd.ctx)
    cmd.need(gp["message"], "أضف مجموعات أول بـ `.اضف_مجموعة`")
    link = cmd.args.strip()
    cmd.need(link, "اكتب الرابط بعد الأمر.")
    cmd.need(link not in gp["links"], "الرابط موجود بالفعل.")
    errs = await _start_group_tasks(None, cmd.client, cmd.ctx, [link], gp["message"], gp["delay"], gp["count"])
    cmd.need(not errs, errs[0] if errs else "")
    gp["links"].append(link)
    gp["sent"][link] = 0
    await cmd.edit(f"✅ **تمت إضافة الرابط وبدأ النشر:** `{link}`")


@command(".ازالة_رابط_مجموعة", section="publish", usage=".ازالة_رابط_مجموعة <رابط>", desc="حذف رابط من قائمة النشر")
async def remove_group(cmd):
    gp = _gp(cmd.ctx)
    link = cmd.args.strip()
    cmd.need(link in gp["links"], "هذا الرابط مو بالقائمة.")
    t = gp["tasks"].pop(link, None)
    if t:
        t.cancel()
    gp["links"].remove(link)
    gp["sent"].pop(link, None)
    await cmd.edit("✅ **تم حذف الرابط وإيقاف النشر فيه.**")


@command(".تغيير_كليشة_مجموعة", section="publish", usage=".تغيير_كليشة_مجموعة <الكليشة الجديدة>",
         desc="تغيير الكليشة وإعادة تشغيل النشر بكل المجموعات")
async def change_text(cmd):
    gp = _gp(cmd.ctx)
    cmd.need(gp["links"], "ما في مجموعات محفوظة.")
    cmd.need(cmd.args, "اكتب الكليشة الجديدة بعد الأمر.")
    for t in gp["tasks"].values():
        t.cancel()
    gp["tasks"].clear()
    gp["message"] = cmd.args
    gp["sent"] = {l: 0 for l in gp["links"]}
    errs = await _start_group_tasks(None, cmd.client, cmd.ctx, list(gp["links"]), cmd.args, gp["delay"], gp["count"])
    await cmd.edit("✅ **تم تغيير الكليشة وإعادة النشر.**" + ("\n" + "\n".join(errs) if errs else ""))
