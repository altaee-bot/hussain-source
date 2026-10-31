"""
كتالوج الأوامر — يتولّد تلقائياً من الأوامر المسجّلة بـ @command.
أي أمر جديد تضيفه يظهر بالقوائم (.م1 … و .اوامر و .اوامر_كل) بدون ما تعدّل شي هنا.
"""
from core import framework
from core.constants import CHANNEL, DEV_USER, SOURCE_NAME, VERSION
from core.ui import LINE

# (رقم، مفتاح القسم، أيقونة، العنوان)
SECTIONS = [
    (1, "account", "⚙️", "الحساب والتنسيق"),
    (2, "replies", "💬", "الردود والترحيب"),
    (3, "media", "🎵", "الميديا والتحميل"),
    (4, "moderation", "🛡️", "الإدارة والتحكم"),
    (5, "time", "⏰", "الوقت والزخارف"),
    (6, "hunting", "🎯", "الصيد والتثبيت"),
    (7, "fun", "🎭", "التسلية والمرح"),
    (8, "protection", "⚔️", "الحماية والتحذيرات"),
    (9, "publish", "📢", "النشر والتكرار"),
    (10, "ai", "🧠", "الذكاء والصنع"),
    (11, "system", "🖥️", "النظام والمعلومات"),
    (12, "memes", "🔊", "الميمز والصوتيات"),
    (13, "tools", "🧰", "أدوات مفيدة"),
    (14, "games", "🎮", "ألعاب وأسئلة"),
]
_BY_NUM = {s[0]: s for s in SECTIONS}
_BY_KEY = {s[1]: s for s in SECTIONS}

# أقسام تعرض سطوراً إضافية (مثل قائمة الميمز) — القيمة دالة ترجع list[str]
EXTRA_LINES = {}


def section(num):
    return _BY_NUM.get(int(num))


def commands_of(key):
    """أوامر قسم (غير المخفية) بترتيب التسجيل، بدون تكرار."""
    out, seen = [], set()
    for spec in framework.REGISTRY:
        if spec.section == key and not spec.hidden and spec.names[0] not in seen:
            seen.add(spec.names[0])
            out.append(spec)
    return out


def counts():
    return {s[0]: len(commands_of(s[1])) for s in SECTIONS}


def _line(spec):
    shown = spec.usage or spec.names[0]
    alias = ""
    if len(spec.names) > 1:
        alias = "  ‹" + " · ".join(spec.names[1:3]) + "›"
    d = f" — {spec.desc}" if spec.desc else ""
    return f"• `{shown}`{d}{alias}"


def help_text(num, limit=3900):
    sec = section(num)
    if not sec:
        return "❌ هذا القسم غير موجود. أرسل `.م` لعرض كل الأقسام."
    _, key, icon, title = sec
    lines = [f"**{icon} {title} (م{num})**", LINE]
    lines += [_line(s) for s in commands_of(key)]
    fn = EXTRA_LINES.get(key)
    if fn:
        lines += [LINE] + list(fn())
    lines += [LINE, f"📡 {CHANNEL} • 👨‍💻 {DEV_USER}"]
    text = "\n".join(lines)
    if len(text) > limit:
        text = text[:limit].rsplit("\n", 1)[0] + f"\n… (القائمة كاملة بالأمر `.م{num}` داخل الدردشة)"
    return text


def main_menu_text():
    c = counts()
    rows = [f"**╭━━〔 🦅 {SOURCE_NAME} {VERSION} 🦅 〕━━╮**", "",
            "👑 **أهلاً بك في مملكة أوامر ريكو**", LINE]
    for num, key, icon, title in SECTIONS:
        rows.append(f"{icon} **{title}** ⇦ `.م{num}`  ‹{c[num]}›")
    rows += [LINE, f"🖱 **قائمة بالأزرار:** `.اوامر`    📖 **كل الأوامر:** `.اوامر_كل`",
             f"⚜️ **المطور** ⇦ {DEV_USER}", f"🚀 **القناة** ⇦ {CHANNEL}", "",
             "**╰━━〔 ⚡️ RECO ⚡️ 〕━━╯**"]
    return "\n".join(rows)


def all_commands_text():
    parts = []
    for num, key, icon, title in SECTIONS:
        specs = commands_of(key)
        if not specs:
            continue
        names = "  ".join(f"`{s.names[0]}`" for s in specs)
        parts.append(f"**{icon} {title} (م{num})**\n{names}")
    total = sum(counts().values())
    return (f"**🌀 كل أوامر {SOURCE_NAME} ({total} أمر):**\n{LINE}\n" + "\n\n".join(parts)
            + f"\n{LINE}\n💡 تفاصيل أي قسم: `.م<رقم>`  |  📡 {CHANNEL}")
