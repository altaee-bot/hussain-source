"""كلايش وتنسيقات موحّدة لكل الأوامر (تغيير الشكل من هنا يغيّر السورس كله)."""
from core.constants import CHANNEL, DEV_USER

LINE = "‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉"
THIN = "‏─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─"


def ok(text):
    return f"✅ {text}"


def fail(text):
    return f"❌ {text}"


def warn(text):
    return f"⚠️ {text}"


def wait(text):
    return f"⏳ {text}"


def info(text):
    return f"ℹ️ {text}"


def card(title, rows=(), icon="🦅", footer=None):
    """بطاقة موحدة: عنوان + سطور + تذييل اختياري."""
    out = [f"**{icon} {title}**", LINE]
    out.extend(str(r) for r in rows)
    if footer:
        out.extend([LINE, footer])
    return "\n".join(out)


def kv(label, value, icon="•"):
    return f"{icon} **{label}:** {value}"


def mention(user):
    name = (getattr(user, "first_name", None) or getattr(user, "title", None) or "مجهول").replace("[", "(").replace("]", ")")
    return f"[{name}](tg://user?id={user.id})"


def footer():
    return f"📡 {CHANNEL} • 👨‍💻 {DEV_USER}"


def usage(cmd, *lines):
    """رسالة استخدام موحّدة عند نقص المدخلات."""
    body = "\n".join(f"• {l}" for l in lines)
    return f"⚠️ **الصيغة:** `{cmd}`" + (f"\n{body}" if body else "")


def human_size(n):
    n = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def human_dur(sec):
    sec = int(sec or 0)
    h, r = divmod(sec, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def progress_bar(pct, width=12):
    pct = max(0, min(100, pct))
    full = int(width * pct / 100)
    return "█" * full + "░" * (width - full) + f" {pct:.0f}%"
