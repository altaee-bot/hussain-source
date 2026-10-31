"""فحص السورس، البنج، معلومات النظام، معلومات التنصيب."""
import asyncio
import os
import platform
import time
from datetime import datetime

import pytz
from telethon import functions

from core.constants import CHANNEL, DEV_USER, SOURCE_NAME, TIMEZONE, VERSION
from core.framework import command
from core.ui import card, human_size, kv


def _uptime(ctx):
    d = datetime.now() - ctx.start_time
    days, rem = divmod(int(d.total_seconds()), 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} يوم")
    if h:
        parts.append(f"{h} ساعة")
    parts.append(f"{m} دقيقة")
    if not days and not h:
        parts.append(f"{s} ثانية")
    return " و".join(parts)


async def _ping(client):
    t = time.perf_counter()
    await client(functions.PingRequest(ping_id=int(t * 1000) & 0x7FFFFFFF))
    return round((time.perf_counter() - t) * 1000)


@command(".فحص", ".بنج", section="system", usage=".فحص  |  .فحص <يوزر>",
         desc="فحص السورس والبنج الحقيقي (مع يوزر = فحص توفره)")
async def check(cmd):
    if cmd.args:
        from plugins.hunting.tools import check_username
        return await check_username(cmd)
    me = await cmd.ctx.get_me()
    ping = await _ping(cmd.client)
    now = datetime.now(pytz.timezone(TIMEZONE)).strftime("%I:%M:%S %p")
    text = card(f"تقرير فحص {SOURCE_NAME}", [
        kv("صاحب الحساب", f"[{me.first_name}](tg://user?id={me.id})", "👑"),
        kv("البنج", f"`{ping}ms`", "📡"),
        kv("مدة التشغيل", _uptime(cmd.ctx), "⏱"),
        kv("الوقت الآن", f"`{now}`", "⏰"),
        kv("الإصدار", f"`{VERSION}`", "🏷"),
        kv("الحالة", "`ACTIVE ✅`", "⚙️"),
    ], footer=f"👨‍💻 {DEV_USER} | 📡 {CHANNEL}")
    photo = "f.jpg"
    if cmd.is_owner and os.path.exists(photo):
        await cmd.client.send_file(cmd.chat_id, photo, caption=text)
        return await cmd.delete()
    await cmd.edit(text)


@command(".نظام", ".نظامي", section="system", desc="معلومات السيرفر: المعالج، الرام، التخزين")
async def system(cmd):
    rows = [kv("النظام", f"`{platform.system()} {platform.release()}`", "🖥"),
            kv("بايثون", f"`{platform.python_version()}`", "🐍")]
    try:
        import psutil
        vm, du = psutil.virtual_memory(), psutil.disk_usage("/")
        rows += [kv("المعالج", f"`{psutil.cpu_percent(interval=0.3)}%` ({psutil.cpu_count()} نواة)", "⚙️"),
                 kv("الرام", f"`{human_size(vm.used)} / {human_size(vm.total)}` ({vm.percent}%)", "🧠"),
                 kv("التخزين", f"`{human_size(du.used)} / {human_size(du.total)}` ({du.percent}%)", "💾")]
        proc = psutil.Process()
        rows.append(kv("رام السورس", f"`{human_size(proc.memory_info().rss)}`", "📊"))
    except ImportError:
        load = os.getloadavg() if hasattr(os, "getloadavg") else None
        if load:
            rows.append(kv("الحمل", f"`{load[0]:.2f}`", "⚙️"))
        rows.append("💡 ثبّت `psutil` لتفاصيل أكثر: `pip install psutil`")
    rows.append(kv("مدة التشغيل", _uptime(cmd.ctx), "⏱"))
    await cmd.edit(card("حالة السيرفر", rows))


@command(".تنصيبي", section="system", desc="معلومات التنصيب (الإصدار، التاريخ، المطور)")
async def install_info(cmd):
    me = await cmd.ctx.get_me()
    info = cmd.ctx.install_info or {}
    rows = [kv("اسم السورس", SOURCE_NAME, "📦"), kv("الإصدار", f"`{VERSION}`", "🏷"),
            kv("المنصّب", f"[{me.first_name}](tg://user?id={me.id})", "👤"),
            kv("الايدي", f"`{me.id}`", "🆔"),
            kv("تاريخ التنصيب", f"`{info.get('date', 'غير معروف')}`", "📅"),
            kv("القناة", CHANNEL, "📡"), kv("المطور", DEV_USER, "👨‍💻")]
    await cmd.edit(card("معلومات التنصيب", rows, icon="🧩", footer="شكراً لاستخدامك سورس ريكو 🦅"))


@command(".المطور", section="system", desc="معلومات مطور السورس وقناته")
async def developer(cmd):
    await cmd.edit(card("مطور السورس", [kv("المطور", DEV_USER, "👨‍💻"), kv("القناة", CHANNEL, "📢")]))


@command(".ترحيب_مطور", section="system", hidden=True, anyone=True)
async def dev_hello(cmd):
    """يرد حالة السورس عندما يرسل مطور السورس هذا الأمر."""
    sender = await cmd.event.get_sender()
    uname = (getattr(sender, "username", None) or "").lower()
    if uname != DEV_USER.lstrip("@").lower():
        return
    me = await cmd.ctx.get_me()
    await cmd.event.reply(card(f"{SOURCE_NAME} يعمل بنجاح", [
        kv("المنصّب", f"[{me.first_name}](tg://user?id={me.id})", "👤"),
        kv("مدة التشغيل", _uptime(cmd.ctx), "⏱"), kv("الحالة", "`فعال ✅`", "⚙️")], icon="🛡"))


@command(".اعادة_تشغيل", section="system", desc="إعادة تشغيل السورس")
async def restart(cmd):
    import sys
    await cmd.edit("♻️ **جاري إعادة التشغيل...**")
    await asyncio.sleep(1)
    os.execl(sys.executable, sys.executable, *sys.argv)
