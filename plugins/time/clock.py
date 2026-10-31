"""الساعة داخل الاسم (تعمل بالخلفية وتُستأنف تلقائياً بعد إعادة التشغيل) + الوقت والتاريخ."""
import asyncio
from datetime import datetime

import pytz
from telethon import functions

from core.constants import TIMEZONE
from core.fonts import STYLES, clean_name, style_time
from core.framework import CmdError, command, on_start
from core.ui import card, kv

DAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
MONTHS = ["كانون الثاني", "شباط", "آذار", "نيسان", "أيار", "حزيران", "تموز", "آب", "أيلول",
          "تشرين الأول", "تشرين الثاني", "كانون الأول"]

CITIES = {
    "بغداد": "Asia/Baghdad", "الرياض": "Asia/Riyadh", "دبي": "Asia/Dubai", "الكويت": "Asia/Kuwait",
    "قطر": "Asia/Qatar", "عمان": "Asia/Amman", "القاهرة": "Africa/Cairo", "دمشق": "Asia/Damascus",
    "بيروت": "Asia/Beirut", "طهران": "Asia/Tehran", "اسطنبول": "Europe/Istanbul", "لندن": "Europe/London",
    "باريس": "Europe/Paris", "برلين": "Europe/Berlin", "موسكو": "Europe/Moscow", "نيويورك": "America/New_York",
    "لوس انجلس": "America/Los_Angeles", "طوكيو": "Asia/Tokyo", "سيول": "Asia/Seoul", "بكين": "Asia/Shanghai",
    "سيدني": "Australia/Sydney", "الجزائر": "Africa/Algiers", "الرباط": "Africa/Casablanca", "تونس": "Africa/Tunis",
}


def _render(style, tz):
    fmt = "%I:%M %p" if style == "0" else "%I:%M"
    return style_time(datetime.now(tz).strftime(fmt), style)


async def _clock_loop(client, ctx, style):
    tz = pytz.timezone(TIMEZONE)
    last = None
    while True:
        try:
            me = await ctx.get_me(refresh=True)
            base = ctx.state.get("time_base") or clean_name(me.first_name)
            new = f"{base} | {_render(style, tz)}"
            if new != last:
                await client(functions.account.UpdateProfileRequest(first_name=new[:64]))
                last = new
        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"⚠️ ساعة الاسم: {e}")
        # ننام لبداية الدقيقة الجاية بالضبط (تحديث دقيق وبدون طلبات زايدة)
        await asyncio.sleep(61 - datetime.now().second)


def _start(ctx, style):
    if ctx.time_task and not ctx.time_task.done():
        ctx.time_task.cancel()
    ctx.time_task = asyncio.create_task(_clock_loop(ctx.client, ctx, style))


@command(".وقت_تشغيل", section="time", numeric_suffix=True, usage=".وقت_تشغيل[0-13]",
         desc="ساعة بتوقيت بغداد داخل اسمك (الرقم = شكل الأرقام) — تبقى شغالة بعد إعادة التشغيل")
async def clock_on(cmd):
    style = cmd.suffix or (cmd.words[0] if cmd.words and cmd.words[0].isdigit() else "0")
    if style not in STYLES:
        raise CmdError("الأنماط المتاحة من 0 إلى 13 — شوفها بـ `.م5`")
    me = await cmd.ctx.get_me(refresh=True)
    base = clean_name(me.first_name)
    cmd.ctx.state.data["time_base"] = base
    cmd.ctx.state.set("time_style", style)
    _start(cmd.ctx, style)
    sample = _render(style, pytz.timezone(TIMEZONE))
    await cmd.edit(card(f"تم تفعيل الساعة (نمط {style})", [kv("الشكل", f"`{base} | {sample}`", "👤"),
                                                        "📴 للإيقاف: `.وقت_إطفاء`"], icon="👑"))


@command(".وقت_إطفاء", section="time", desc="إيقاف الساعة وإرجاع اسمك الأصلي")
async def clock_off(cmd):
    ctx = cmd.ctx
    if not ctx.time_task and not ctx.state.get("time_style"):
        raise CmdError("الساعة غير مفعّلة أصلاً.")
    if ctx.time_task:
        ctx.time_task.cancel()
        ctx.time_task = None
    me = await ctx.get_me(refresh=True)
    name = ctx.state.get("time_base") or clean_name(me.first_name)
    await cmd.client(functions.account.UpdateProfileRequest(first_name=name))
    ctx.state.data.pop("time_style", None)
    ctx.state.data.pop("time_base", None)
    ctx.save()
    await ctx.get_me(refresh=True)
    await cmd.edit(f"📴 **تم إيقاف الساعة وإرجاع اسمك:** `{name}`")


@on_start
async def resume_clock(ctx):
    style = ctx.state.get("time_style")
    if style in STYLES:
        _start(ctx, style)


@command(".الوقت", ".توقيت", section="time", usage=".الوقت [مدينة]", desc="الوقت والتاريخ الآن (بغداد أو أي مدينة)")
async def now(cmd):
    city = cmd.args.strip() or "بغداد"
    zone = CITIES.get(city)
    if not zone:
        raise CmdError("المدينة غير مدعومة. المتاحة:\n" + "، ".join(CITIES))
    t = datetime.now(pytz.timezone(zone))
    await cmd.edit(card(f"الوقت في {city}", [
        kv("الساعة", f"`{t.strftime('%I:%M:%S %p')}`", "⏰"),
        kv("اليوم", f"{DAYS[t.weekday()]}", "📅"),
        kv("التاريخ", f"`{t.day} {MONTHS[t.month - 1]} {t.year}`", "🗓")]))


@command(".تاريخ", section="time", desc="تاريخ اليوم")
async def today(cmd):
    t = datetime.now(pytz.timezone(TIMEZONE))
    await cmd.edit(f"📅 **{DAYS[t.weekday()]} {t.day} {MONTHS[t.month - 1]} {t.year}**  ({t.strftime('%Y/%m/%d')})")
