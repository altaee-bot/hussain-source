"""مقالب وهمية (محاكاة فقط — ما تسوي أي اختراق حقيقي) + دراما اجتماعية بالرد."""
import asyncio
import random

from core.constants import DEV_USER
from core.framework import command
from core.ui import LINE, mention


async def _victim(cmd):
    user = await cmd.target(allow_self=False)
    return user


async def _play(cmd, steps, delay, fmt="`{}`", head=None):
    for s in steps:
        await cmd.event.edit(f"{head}\n{fmt.format(s)}" if head else fmt.format(s))
        await asyncio.sleep(delay)


@command(".هاك", section="fun", usage=".هاك (بالرد)", desc="الهجوم العملاق الوهمي 💀 (محاكاة للمزح فقط)")
async def mega_hack(cmd):
    user = await _victim(cmd)
    steps = [
        "📡 Connecting to Global Satellites... [OK]", "🔐 Bypassing Telegram Cloud Encryption...",
        "🕵️ Tracking User IP: [192.168.0.104]...", "📡 Signal Found: Baghdad/Al-Mansour",
        "💾 Accessing Private Gallery... [15%]", "⚠️ FIREWALL DETECTED: [Attempting Bypass]",
        "🛡️ Injecting Script: (Rico_V16.py)", "✅ Firewall Destroyed. Accessing System Root...",
        "📱 Device Model: [iPhone 15 Pro Max] Found.", "📸 Opening Front Camera... [SUCCESS]",
        "📂 Fetching Saved Passwords (Google/FB/IG)...", "🔑 142 Passwords Found. Saving to Server...",
        "🧬 Extracting Biometric Data (FaceID/TouchID)...", "🚨 WARNING: Device Temperature Rising!",
        "📥 Finalizing Data Transfer: (14.2 GB)...", "💥 Injecting Fatal System Virus...",
    ]
    bars = ["▒▒▒▒▒▒▒▒▒▒", "██▒▒▒▒▒▒▒▒", "████▒▒▒▒▒▒", "██████▒▒▒▒", "████████▒▒", "██████████"]
    for i, s in enumerate(steps):
        icon = random.choice(["☣️", "💀", "💻", "🛰️", "⚙️", "🔥"])
        pct = int((i + 1) / len(steps) * 100)
        await cmd.event.edit(f"{icon} **[ULTRA HACK ACTIVE]** {icon}\n`{s}`\n`[{bars[min(5, i * 6 // len(steps))]}] {pct}%`")
        await asyncio.sleep(1.6)
    await cmd.event.edit(
        f"**🔥 تـم اخـتـراق الـهـدف بـنـجـاح كـامـل 🔥**\n{LINE}\n👤 الضحية: {mention(user)}\n🆔 الايدي: `{user.id}`\n{LINE}\n"
        f"☠️ **جاري مسح الذاكرة الداخلية...**\n☠️ **جاري رفع الملفات للسيرفر...**\n💸 **للنجاة تواصل مع المطور {DEV_USER}**\n"
        f"{LINE}\n😂 **مزحة! ما صار أي شي — بس لا تخاف** 💀")


@command(".اختراق", section="fun", usage=".اختراق (بالرد)", desc="محاكاة اختراق قصيرة (وهمية)")
async def hack_sim(cmd):
    user = await _victim(cmd)
    await cmd.edit("📡 **جاري سحب بيانات الضحية...**")
    await asyncio.sleep(1)
    await _play(cmd, [f"👤 Target ID: {user.id}", "🔓 Password Cracking: [SUCCESS]", "📍 Location: Baghdad, Iraq",
                      "📸 Accessing Camera: [LIVE ON]"], 0.9, head="⚠️ **ATTACKING...**")
    await cmd.event.edit("💀 **تم الاختراق! الضحية الآن تحت سيطرتك.** 😂 (مزحة)")


@command(".هعر", ".هكر", section="fun", usage=".هعر (بالرد)", desc="محاولة اختراق تفشل (فيروس)")
async def hack_fail(cmd):
    await _victim(cmd)
    await cmd.edit("☣️ **محاولة اختراق النظام الدفاعي...**")
    await asyncio.sleep(1.2)
    await _play(cmd, ["📡 محاولة كسر جدار الحماية...", "⚠️ تحذير: تم اكتشاف محاولة الدخول!",
                      "🛡 نظام الحماية مفعل حالياً.", "🚫 ERROR: Access Denied!"], 1.0, head="⚙️ **جاري الاختراق:**")
    await cmd.event.edit("❌ **فـشـل الاخـتـراق!**\nنظام حماية المستخدم قوي جداً، تم صد الهجوم 🛡")


# ───────────────────────── دراما
@command(".زواج", section="fun", usage=".زواج (بالرد)", desc="عقد قران مبارك 👰🤵")
async def marriage(cmd):
    user = await _victim(cmd)
    me = await cmd.ctx.get_me()
    await cmd.edit(f"**💍 تـم عـقـد الـقـران بـنـجـاح! 💍**\n{LINE}\n👰 **الـعـروس:** {mention(user)}\n🤵 **الـعـريـس:** {mention(me)}\n"
                   f"🎊 ألف مبروك للعرسان الحلوين!\n✨ بارك الله لكما وجمع بينكما بخير.\n{LINE}\n🎶 *جاري تحضير الكيك والدي جي...* 💃🕺")


@command(".طلاق", section="fun", usage=".طلاق (بالرد)", desc="ورقة طلاق رسمية 💔")
async def divorce(cmd):
    user = await _victim(cmd)
    reasons = ["لأنك ما تغسل مواعين 🍽️", "لأنك تنام هواي وتنسى الطلبات 💤", "بسبب الخيانة مع سورس ثاني 💔",
               "لأنك تصرف فلوسنا على شدات ببجي 🎮", "ماكو توافق كيميائي بيننا! 🧪", "لأنك تحجي وية الكل إلا أني 📵"]
    await cmd.edit(f"**💔 ورقة طـلاق رسـمـيـة 💔**\n{LINE}\nقرر الطرف الأول الانفصال عن:\n👤 {mention(user)}\n"
                   f"⚠️ **السبب:** {random.choice(reasons)}\n⚖️ الـحـالـة: أنتِ طالق طالق طالق! 👞\n{LINE}\n👋 باي باي.. درب السد ما يرد!")


@command(".خيانه", ".خيانة", section="fun", usage=".خيانه (بالرد)", desc="بلاغ خيانة عظمى 🕵️ (دراما للمزح)")
async def betrayal(cmd):
    user = await _victim(cmd)
    me = await cmd.ctx.get_me()
    scenes = ["شفتك بالحديقة وية سورس ثاني! 🌳", "ليش راد على ستوري غيري ومنطيني بلوك؟ 📱💔",
              "طلعت تحجي وية المطور من وراي! 🕵️‍♂️", "لكيت صورتك بملفات سورس ثاني، هاي خيانة عظمى! 📂🚫"]
    await cmd.edit(f"**🔥 بـلاغ خـيـانـة عـظـمـى! 🔥**\n{LINE}\n👤 الضحية: {mention(me)}\n🕵️ المتهم: {mention(user)}\n"
                   f"📢 **التصريح:** \"{random.choice(scenes)}\"\n⚖️ **قرار المحكمة العليا لريكو:** فسخ العلاقة فوراً والاكتفاء بنظرة عتاب!\n"
                   f"{LINE}\n💔 انتهت القصة.. يا للأسف!")


@command(".حب", section="fun", usage=".حب (بالرد)", desc="نسبة الحب بينك وبين الشخص ❤️")
async def love(cmd):
    user = await _victim(cmd)
    me = await cmd.ctx.get_me()
    # نسبة ثابتة لنفس الثنائي بنفس اليوم (مو عشوائية كل مرة)
    seed = f"{min(me.id, user.id)}-{max(me.id, user.id)}-{__import__('datetime').date.today()}"
    pct = random.Random(seed).randint(5, 100)
    bar = "❤️" * (pct // 10) + "🤍" * (10 - pct // 10)
    await cmd.edit(f"💘 **نسبة الحب بين {mention(me)} و {mention(user)}**\n{bar}\n**{pct}%** " +
                   ("🔥 حب الأساطير!" if pct > 85 else "😍 حلو!" if pct > 60 else "🙂 عادي" if pct > 35 else "💔 مو نصيب"))


@command(".كشف", section="fun", usage=".كشف (بالرد)", desc="جهاز كشف الكذب 🔍")
async def lie_detector(cmd):
    user = await _victim(cmd)
    for frame in ("🔍 جاري الفحص", "🔍 جاري الفحص.", "🔍 جاري الفحص..", "🔍 جاري الفحص..."):
        await cmd.event.edit(frame)
        await asyncio.sleep(0.5)
    res = random.choice(["كاذب 🤥", "صادق ✅", "نص نص 🤔", "يكذب بس يحلو الكذب 😏"])
    await cmd.event.edit(f"🔍 **نتيجة جهاز كشف الكذب لـ {mention(user)}:** {res}")


@command(".رفع", section="fun", usage=".رفع <شي> (بالرد)  مثال: .رفع ملك", desc="رفع الشخص لرتبة مضحكة 😂 (ملك، وزير، بطل، أسطورة...)")
async def raise_user(cmd):
    user = await _victim(cmd)
    title = cmd.rest.strip() or cmd.args.replace(f"@{getattr(user, 'username', '')}", "").strip() or "ملك"
    icon = {"ملك": "👑", "وزير": "🎩", "بطل": "🏆", "أسطورة": "🌟", "قائد": "🎖", "نجم": "⭐", "رئيس": "💼"}.get(title, "🎖")
    await cmd.edit(f"{icon} **تم رفع** {mention(user)} **{title}** بنجاح!\n🎉 مبروك الرتبة الجديدة!")


@command(".اختراق1", section="fun", usage=".اختراق1 (بالرد)", desc="اختراق وهمي مطوّل (مزح فقط)")
async def deep_hack(cmd):
    user = await _victim(cmd)
    steps = ["🔍 Scanning for vulnerabilities...", "🛡 Bypass Firewall: [██░░░░░░░░] 20%", "🔓 Exploit Found: (CVE-2026-9912)",
             "🧬 Brute-forcing Encryption: [████░░░░░░] 40%", "📥 Accessing Internal Memory: [██████░░░░] 60%",
             "🎭 Spoofing User Identity...", "💾 Downloading Personal Data: [████████░░] 80%",
             "📸 Activating Microphone & Camera...", "📊 Finalizing Injection: [██████████] 100%", "💀 ALL SYSTEMS COMPROMISED."]
    await cmd.edit("📡 **[SYSTEM]: Initializing Deep-Core Attack...**")
    await asyncio.sleep(1.5)
    await _play(cmd, steps, 1.3, head="☠️ **[HACKER MODE ACTIVE]**")
    await cmd.event.edit(f"🔥 **تـم تدمـيـر الحسـاب بنـجاح!** (مزحة 😂)\nالضحية: {mention(user)}\nالحالة: **تحت السيطرة الكاملة ✅**")
