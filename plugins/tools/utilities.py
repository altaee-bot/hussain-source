"""أدوات مفيدة: ترجمة، طقس، أوقات الصلاة، حاسبة، QR، اختصار روابط، عملات، عمر، سرعة النت، نصوص."""
import ast
import asyncio
import base64
import io
import math
import operator
import random
from datetime import date

from core import netutil
from core.framework import CmdError, command
from core.ui import card, kv, LINE

# ───────────────────────── الترجمة
LANGS = {"عربي": "ar", "العربية": "ar", "انجليزي": "en", "انكليزي": "en", "تركي": "tr", "فارسي": "fa", "فرنسي": "fr",
         "الماني": "de", "اسباني": "es", "روسي": "ru", "كردي": "ku", "هندي": "hi", "ياباني": "ja", "صيني": "zh-CN",
         "كوري": "ko", "ايطالي": "it", "برتغالي": "pt", "اردو": "ur", "عبري": "iw", "يوناني": "el", "هولندي": "nl"}


@command(".ترجمة", ".ترجم", section="tools", usage=".ترجمة <لغة> <نص>   أو بالرد: .ترجمة انجليزي",
         desc="ترجمة نص. اللغات: عربي، انجليزي، تركي، فارسي، فرنسي، الماني، اسباني، روسي، كردي... (أو رمز مثل en)")
async def translate(cmd):
    from deep_translator import GoogleTranslator
    words = cmd.args.split()
    target, text = "ar", ""
    if words:
        w0 = words[0].lower()
        if w0 in LANGS or w0 in LANGS.values():
            target = LANGS.get(w0, w0)
            text = " ".join(words[1:])
        else:
            text = cmd.args
    r = await cmd.reply_msg()
    if not text and r is not None:
        text = r.raw_text or ""
    cmd.need(text, "اكتب النص أو رد على رسالة. مثال: `.ترجمة انجليزي مرحبا بالعالم`")
    out = await asyncio.to_thread(lambda: GoogleTranslator(source="auto", target=target).translate(text[:4500]))
    await cmd.edit(card(f"الترجمة → {target}", [out or "—"], icon="🌐"))


# ───────────────────────── الطقس
@command(".طقس", section="tools", usage=".طقس [مدينة]", desc="حالة الطقس الآن (افتراضياً بغداد). اكتب اسم المدينة بالانجليزي للدقة")
async def weather(cmd):
    city = cmd.args.strip() or "Baghdad"
    data = await netutil.get_json(f"https://wttr.in/{city}", params={"format": "j1", "lang": "ar"})
    cur = data["current_condition"][0]
    desc = (cur.get("lang_ar") or cur.get("weatherDesc") or [{"value": ""}])[0]["value"]
    area = data.get("nearest_area", [{}])[0].get("areaName", [{"value": city}])[0]["value"]
    today = data["weather"][0]
    await cmd.edit(card(f"طقس {area}", [
        kv("الحالة", desc, "🌤"), kv("الحرارة", f"`{cur['temp_C']}°C` (تحس بـ `{cur['FeelsLikeC']}°C`)", "🌡"),
        kv("الرطوبة", f"`{cur['humidity']}%`", "💧"), kv("الرياح", f"`{cur['windspeedKmph']} كم/س`", "💨"),
        kv("اليوم", f"أعلى `{today['maxtempC']}°` / أدنى `{today['mintempC']}°`", "📈")], icon="☁️"))


# ───────────────────────── الصلاة
CITIES_PRAYER = {"بغداد": ("Baghdad", "Iraq"), "النجف": ("Najaf", "Iraq"), "كربلاء": ("Karbala", "Iraq"),
                 "البصرة": ("Basra", "Iraq"), "الموصل": ("Mosul", "Iraq"), "اربيل": ("Erbil", "Iraq"),
                 "الحلة": ("Hillah", "Iraq"), "الرياض": ("Riyadh", "Saudi Arabia"), "مكة": ("Makkah", "Saudi Arabia"),
                 "القاهرة": ("Cairo", "Egypt"), "دبي": ("Dubai", "UAE"), "عمان": ("Amman", "Jordan"),
                 "اسطنبول": ("Istanbul", "Turkey"), "طهران": ("Tehran", "Iran")}
PRAYER_NAMES = [("Fajr", "الفجر"), ("Sunrise", "الشروق"), ("Dhuhr", "الظهر"), ("Asr", "العصر"),
                ("Maghrib", "المغرب"), ("Isha", "العشاء")]


@command(".صلاة", ".اوقات_الصلاة", section="tools", usage=".صلاة [مدينة] [جعفري]",
         desc="أوقات الصلاة اليوم (افتراضي بغداد). أضف كلمة `جعفري` للتوقيت الجعفري")
async def prayer(cmd):
    words = cmd.words
    jafari = "جعفري" in words
    name = next((w for w in words if w != "جعفري"), "بغداد")
    city, country = CITIES_PRAYER.get(name, (name, ""))
    params = {"city": city, "country": country or "Iraq", "method": 0 if jafari else 3}
    data = await netutil.get_json("https://api.aladhan.com/v1/timingsByCity", params=params)
    t = data["data"]["timings"]
    rows = []
    for key, ar in PRAYER_NAMES:
        h, m = map(int, t[key].split(" ")[0].split(":"))
        rows.append(kv(ar, f"`{(h % 12) or 12}:{m:02d} {'م' if h >= 12 else 'ص'}`", "🕌"))
    await cmd.edit(card(f"أوقات الصلاة — {name}" + (" (جعفري)" if jafari else ""), rows,
                        footer=data["data"]["date"]["hijri"]["date"] + " هـ"))


AZKAR = [
    "سبحان الله وبحمده، سبحان الله العظيم.", "لا إله إلا الله وحده لا شريك له، له الملك وله الحمد وهو على كل شيء قدير.",
    "أستغفر الله العظيم وأتوب إليه.", "اللهم صلّ وسلم على نبينا محمد وآل محمد.", "لا حول ولا قوة إلا بالله العلي العظيم.",
    "حسبي الله لا إله إلا هو عليه توكلت وهو رب العرش العظيم.", "اللهم إني أسألك العفو والعافية في الدنيا والآخرة.",
    "ربنا آتنا في الدنيا حسنة وفي الآخرة حسنة وقنا عذاب النار.", "يا حي يا قيوم برحمتك أستغيث.",
    "اللهم اغفر لي ولوالديّ وللمؤمنين والمؤمنات.", "بسم الله الذي لا يضر مع اسمه شيء في الأرض ولا في السماء وهو السميع العليم.",
    "اللهم أعني على ذكرك وشكرك وحسن عبادتك.", "رضيت بالله رباً وبالإسلام ديناً وبمحمد نبياً.",
    "اللهم عجّل لوليك الفرج واجعلنا من أنصاره وأعوانه.", "سبحان الله، والحمد لله، ولا إله إلا الله، والله أكبر.",
    "اللهم لا سهل إلا ما جعلته سهلاً، وأنت تجعل الحزن إذا شئت سهلاً.", "يا رب لك الحمد كما ينبغي لجلال وجهك وعظيم سلطانك.",
]


@command(".اذكار", ".ذكر", section="tools", desc="ذكر أو دعاء عشوائي")
async def azkar(cmd):
    await cmd.edit(f"🤲 **{random.choice(AZKAR)}**")


# ───────────────────────── الحاسبة (آمنة: بدون eval)
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow,
        ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "log": math.log10, "ln": math.log,
          "abs": abs, "round": round, "floor": math.floor, "ceil": math.ceil, "fact": math.factorial}
_CONSTS = {"pi": math.pi, "e": math.e}


def safe_eval(expr):
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and (abs(b) > 1000 or abs(a) > 1e9):
                raise ValueError("رقم كبير جداً")
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Name) and n.id in _CONSTS:
            return _CONSTS[n.id]
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS and len(n.args) <= 2:
            return _FUNCS[n.func.id](*[ev(a) for a in n.args])
        raise ValueError("عملية غير مدعومة")
    return ev(ast.parse(expr, mode="eval"))


@command(".احسب", ".حاسبة", section="tools", usage=".احسب 2*(3+4)", desc="حاسبة آمنة: + - * / ^ % وجذر `sqrt()` وغيرها")
async def calc(cmd):
    expr = (cmd.args.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
            .replace("×", "*").replace("÷", "/").replace("^", "**").replace("،", "."))
    cmd.need(expr.strip(), "اكتب العملية: `.احسب 12*(3+4)`")
    try:
        res = safe_eval(expr)
    except ZeroDivisionError:
        cmd.fail("القسمة على صفر!")
    except Exception as e:
        cmd.fail(f"عملية غير صالحة: {e}")
    if isinstance(res, float):
        res = round(res, 10)
        if res == int(res) and abs(res) < 1e15:
            res = int(res)
    await cmd.edit(f"🧮 `{cmd.args}`\n{LINE}\n**= {res:,}**" if isinstance(res, (int, float)) else f"= {res}")


# ───────────────────────── QR واختصار
@command(".qr", ".كيوار", section="tools", usage=".qr <نص أو رابط>", desc="إنشاء باركود QR من نص أو رابط")
async def qr(cmd):
    import qrcode
    text = cmd.args
    r = await cmd.reply_msg()
    if not text and r:
        text = r.raw_text or ""
    cmd.need(text, "اكتب النص أو الرابط.")
    img = await asyncio.to_thread(lambda: qrcode.make(text[:1000]))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    buf.name = "reco_qr.png"
    await cmd.client.send_file(cmd.chat_id, buf, caption="📱 **QR Code**\n🦅 RECO", reply_to=cmd.event.reply_to_msg_id)
    await cmd.delete()


@command(".اختصار", section="tools", usage=".اختصار <رابط>", desc="اختصار رابط طويل")
async def shorten(cmd):
    url = cmd.args.strip()
    cmd.need(url.startswith("http"), "ضع رابط يبدأ بـ http")
    short = (await netutil.get_text("https://is.gd/create.php", params={"format": "simple", "url": url})).strip()
    cmd.need(short.startswith("http"), f"تعذر الاختصار: {short[:80]}")
    await cmd.edit(f"🔗 **الرابط المختصر:**\n{short}")


# ───────────────────────── العملات
@command(".عملة", ".تحويل_عملة", section="tools", usage=".عملة 100 USD IQD",
         desc="تحويل العملات (أسعار رسمية عالمية — سعر السوق المحلي قد يختلف)")
async def currency(cmd):
    w = cmd.words
    cmd.need(len(w) >= 2, "الصيغة: `.عملة 100 USD IQD`  (الافتراضي: دولار ← دينار)")
    try:
        amount = float(w[0])
    except ValueError:
        raise CmdError("أول قيمة لازم تكون رقم.")
    src = w[1].upper()
    dst = (w[2] if len(w) > 2 else "IQD").upper()
    data = await netutil.get_json(f"https://open.er-api.com/v6/latest/{src}")
    cmd.need(data.get("result") == "success" and dst in data["rates"], "رمز العملة غير صحيح (مثل USD, EUR, IQD, SAR).")
    await cmd.edit(card("تحويل العملات", [f"💵 **{amount:,.2f} {src}**", f"💰 **= {amount * data['rates'][dst]:,.2f} {dst}**",
                                         f"📊 السعر: `1 {src} = {data['rates'][dst]:,.4f} {dst}`"], icon="💱"))


# ───────────────────────── العمر والسرعة
@command(".عمر", ".حساب_العمر", section="tools", usage=".عمر 1999/5/20", desc="حساب عمرك بالتفصيل ومتى عيد ميلادك")
async def age(cmd):
    parts = cmd.args.replace("-", "/").replace(".", "/").split("/")
    cmd.need(len(parts) == 3 and all(p.strip().isdigit() for p in parts), "اكتب التاريخ: `.عمر 1999/5/20`")
    try:
        y, m, d = map(int, parts)
        b = date(y, m, d)
    except ValueError:
        cmd.fail("تاريخ غير صحيح.")
    today = date.today()
    cmd.need(b < today, "تاريخ الميلاد لازم يكون بالماضي.")
    years = today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    months = (today.month - b.month - (today.day < b.day)) % 12
    nxt = date(today.year, b.month, b.day) if (b.month, b.day) >= (today.month, today.day) else date(today.year + 1, b.month, b.day)
    await cmd.edit(card("حساب العمر", [kv("عمرك", f"`{years}` سنة و`{months}` شهر", "🎂"),
                                       kv("بالأيام", f"`{(today - b).days:,}` يوم", "📅"),
                                       kv("عيد ميلادك القادم", f"بعد `{(nxt - today).days}` يوم 🎉", "🎁")]))


@command(".سرعة", ".سرعة_النت", section="tools", desc="فحص سرعة الانترنت للسيرفر (يأخذ ~30 ثانية)")
async def speed(cmd):
    try:
        import speedtest
    except ImportError:
        cmd.fail("ثبّت المكتبة: `pip install speedtest-cli`")
    await cmd.edit("⏳ **أفحص السرعة... (قد يأخذ نص دقيقة)**")

    def run():
        st = speedtest.Speedtest()
        st.get_best_server()
        return st.download() / 1e6, st.upload() / 1e6, st.results.ping, st.results.server["sponsor"]
    down, up, ping, server = await asyncio.to_thread(run)
    await cmd.edit(card("سرعة الانترنت", [kv("التحميل", f"`{down:.1f} Mbps`", "⬇️"), kv("الرفع", f"`{up:.1f} Mbps`", "⬆️"),
                                          kv("البنج", f"`{ping:.0f} ms`", "📡"), kv("السيرفر", server, "🌍")], icon="🚀"))


# ───────────────────────── نصوص
@command(".اكتب", section="tools", usage=".اكتب <نص>", desc="تأثير الكتابة حرف حرف")
async def typing(cmd):
    text = cmd.args
    cmd.need(text, "اكتب النص بعد الأمر.")
    text = text[:200]
    cur = ""
    step = max(1, len(text) // 25)
    for i in range(0, len(text), step):
        cur = text[:i + step]
        await cmd.event.edit(cur + "█")
        await asyncio.sleep(0.25)
    await cmd.event.edit(text)


@command(".عكس", section="tools", usage=".عكس <نص>", desc="قلب النص (يقرأ من اليمين لليسار)")
async def reverse(cmd):
    cmd.need(cmd.args, "اكتب النص.")
    await cmd.edit(cmd.args[::-1])


@command(".عد", section="tools", usage=".عد <نص> (أو بالرد)", desc="عدد حروف وكلمات وأسطر النص")
async def count(cmd):
    text = cmd.args
    r = await cmd.reply_msg()
    if not text and r:
        text = r.raw_text or ""
    cmd.need(text, "اكتب النص أو رد على رسالة.")
    await cmd.edit(card("إحصائيات النص", [kv("الحروف", f"`{len(text)}`", "🔤"), kv("الكلمات", f"`{len(text.split())}`", "📝"),
                                          kv("الأسطر", f"`{len(text.splitlines())}`", "📄")]))


@command(".تشفير", section="tools", usage=".تشفير <نص>", desc="تشفير النص Base64")
async def b64e(cmd):
    cmd.need(cmd.args, "اكتب النص.")
    await cmd.edit(f"🔐 `{base64.b64encode(cmd.args.encode()).decode()}`")


@command(".فك_تشفير", section="tools", usage=".فك_تشفير <نص مشفر>", desc="فك تشفير Base64")
async def b64d(cmd):
    cmd.need(cmd.args, "اكتب النص المشفر.")
    try:
        out = base64.b64decode(cmd.args.encode(), validate=True).decode()
    except Exception:
        cmd.fail("النص المشفر غير صالح.")
    await cmd.edit(f"🔓 `{out}`")
