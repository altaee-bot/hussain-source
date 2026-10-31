"""الصيد والتثبيت: يوزر محدد، عشوائي (ثلاثي/رباعي/خماسي)، بوتات، فحص التوفر."""
import asyncio
import random
import re

from telethon import functions, types

from core.framework import command
from core.hunting_engine import (MODE_NAMES, DIGITS, LETTERS, hunting_engine, is_available, valid_username)
from core.ui import card


def _name(cmd):
    return cmd.args.split()[0].lstrip("@").strip() if cmd.args else ""


async def check_username(cmd):
    user = _name(cmd)
    cmd.need(user, "اكتب اليوزر بعد الأمر.")
    if not valid_username(user):
        return await cmd.edit(f"❌ اليوزر `@{user}` غير صالح (5-32 حرف، يبدأ بحرف، حروف وأرقام و _ فقط).")
    await cmd.edit(f"🔍 **جاري فحص @{user}...**")
    res = await is_available(cmd.client, user)
    if res is None:
        return await cmd.edit("⚠️ تعذر الفحص الآن (ضغط من تيليجرام)، حاول بعد شوي.")
    await cmd.edit(f"✅ **@{user} متاح للاقتناص!** 🎯\n`.صيد {user}` لتثبيته." if res else f"✖️ **@{user} مأخوذ.**")


async def start_fixed(cmd):
    user = _name(cmd)
    cmd.need(user, "اكتب اليوزر بعد الأمر.")
    cmd.need(valid_username(user), f"اليوزر `@{user}` غير صالح.")
    ctx = cmd.ctx
    cmd.need(user not in ctx.hunting_tasks, f"جاري العمل على @{user} بالفعل.")
    await cmd.edit(f"🚀 **بدأ التثبيت التيربو لـ @{user}...**\n🛑 للإيقاف: `.ايقاف الصيد`")
    ctx.hunting_tasks[user] = asyncio.create_task(hunting_engine(cmd.client, ctx, "fixed", target_user=user, event=cmd.event))


@command(".صيد", section="hunting", usage=".صيد <يوزر>", desc="صيد وتثبيت يوزر محدد (ينشئ قناة ويحجزه أول ما يتحرر)")
async def hunt(cmd):
    await start_fixed(cmd)


async def _random(cmd, mode):
    ctx = cmd.ctx
    cmd.need(mode not in ctx.hunting_tasks, "هذي العملية شغالة بالفعل.")
    await cmd.edit(f"⚙️ **بدأ الصيد العشوائي ({MODE_NAMES[mode]})...**\n🛑 للإيقاف: `.ايقاف الصيد`")
    ctx.hunting_tasks[mode] = asyncio.create_task(hunting_engine(cmd.client, ctx, mode, event=cmd.event))


@command(".صيد_ثلاثيات", section="hunting", desc="صيد يوزرات ثلاثية عشوائية (a_1_z)")
async def hunt3(cmd):
    await _random(cmd, "triple")


@command(".صيد_رباعيات", section="hunting", desc="صيد يوزرات رباعية عشوائية")
async def hunt4(cmd):
    await _random(cmd, "quad")


@command(".صيد_خماسيات", section="hunting", desc="صيد يوزرات خماسية عشوائية")
async def hunt5(cmd):
    await _random(cmd, "penta")


@command(".ايقاف الصيد", ".ايقاف_الصيد", section="hunting", desc="إيقاف كل عمليات الصيد")
async def stop_hunt(cmd):
    ctx = cmd.ctx
    n = len(ctx.hunting_tasks)
    for t in list(ctx.hunting_tasks.values()):
        if isinstance(t, asyncio.Task):
            t.cancel()
    ctx.hunting_tasks.clear()
    await cmd.edit(f"🛑 **تم إيقاف {n} عملية صيد.**" if n else "📊 ما في عمليات صيد شغالة.")


@command(".حالة الصيد", ".حالة_الصيد", section="hunting", desc="عرض عمليات الصيد الجارية")
async def hunt_status(cmd):
    tasks = cmd.ctx.hunting_tasks
    if not tasks:
        return await cmd.edit("📊 **لا توجد عمليات جارية حالياً.**")
    rows = [f"• `{k}` — {'يعمل ✅' if not isinstance(v, asyncio.Task) or not v.done() else 'انتهى'}" for k, v in tasks.items()]
    await cmd.edit(card("العمليات النشطة", rows, icon="🔎"))


@command(".صيد_بوت_ثلاثي", section="hunting", desc="صيد بوتات ثلاثية عبر @BotFather")
async def hunt_bot(cmd):
    ctx, client = cmd.ctx, cmd.client
    cmd.need("bot_hunting" not in ctx.hunting_tasks, "صيد البوتات يعمل بالفعل.")
    await cmd.edit("🤖 **بدأ صيد بوتات ثلاثية...**\n🔕 تم كتم BotFather تلقائياً.\n🛑 للإيقاف: `.ايقاف الصيد`")
    try:
        await client(functions.account.UpdateNotifySettingsRequest(
            peer="@BotFather", settings=types.InputPeerNotifySettings(mute_until=2147483647)))
    except Exception:
        pass
    ctx.hunting_tasks["bot_hunting"] = True
    while "bot_hunting" in ctx.hunting_tasks:
        try:
            part = (random.sample(DIGITS, 2) + random.sample(LETTERS, 1)) if random.random() < 0.5 \
                else (random.sample(LETTERS, 2) + random.sample(DIGITS, 1))
            random.shuffle(part)
            username = f"{''.join(part).upper()}_BOT"
            async with client.conversation("@BotFather", timeout=30) as conv:
                await conv.send_message("/newbot")
                await conv.get_response()
                await conv.send_message("صيد ريكو")
                await conv.get_response()
                await conv.send_message(username)
                resp = await conv.get_response()
                txt = resp.text or ""
                if "Done!" in txt:
                    await client.send_message("me", f"✅ **تم صيد بوت ثلاثي:** @{username}\n\n{txt}")
                    await cmd.event.respond(f"🎯 **تم صيد @{username}!** التفاصيل بالرسائل المحفوظة.")
                    ctx.hunting_tasks.pop("bot_hunting", None)
                    return
                low = txt.lower()
                if "too many attempts" in low or "retry" in low:
                    m = re.search(r"(\d+)", txt)
                    await asyncio.sleep(int(m.group(1)) + 2 if m else 60)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(10)
