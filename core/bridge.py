"""
جسر بين حسابات المستخدمين (userbots) وبوت السورس الرئيسي (اللي توكنه بـ config.py).

ليش نحتاجه؟ حساب المستخدم العادي ما يكدر يرسل أزرار inline. فنخلي البوت الرئيسي
يرسلها بوضع inline (via bot) ونربط ضغطات الأزرار بالأمر اللي ينتظرها بنفس العملية.

الخطوات:
  1) الأمر ينشئ Pending ويطلب من حساب المستخدم:  inline_query(@البوت, "yt:<token>")
  2) البوت (core/inline_bot.py) يجاوب بنتيجة فيها الأزرار، والحساب يضغط عليها = يرسل الرسالة.
  3) ضغطات الأزرار توصل للبوت → يحدّث الرسالة ويضع اختيار المستخدم داخل Pending.
  4) الأمر (الذي ينتظر) يكمل الشغل (تحميل/رفع) ويحدّث الرسالة بالتقدم.
"""
import asyncio
import logging
import secrets
import time

from telethon import errors

log = logging.getLogger("reco")

BOT = None            # TelegramClient للبوت الرئيسي
BOT_USERNAME = None   # بدون @
_PENDING = {}
_WARNED = {"inline": False}


def set_bot(bot, username):
    global BOT, BOT_USERNAME
    BOT, BOT_USERNAME = bot, (username or "").lstrip("@") or None


def available():
    return BOT is not None and BOT_USERNAME is not None


class Pending:
    def __init__(self, owner_id, chat_id, kind, data=None):
        self.token = secrets.token_urlsafe(6)
        self.owner_id = owner_id
        self.chat_id = chat_id
        self.kind = kind
        self.data = data or {}
        self.inline_id = None            # معرف رسالة inline (يُعرف بأول ضغطة)
        self.cancelled = False
        self.created = time.time()
        self.future = asyncio.get_running_loop().create_future()
        self._last_edit = 0.0

    def choose(self, value):
        if not self.future.done():
            self.future.set_result(value)

    def cancel(self):
        self.cancelled = True
        self.choose(None)

    async def wait(self, timeout=180):
        try:
            return await asyncio.wait_for(asyncio.shield(self.future), timeout)
        except asyncio.TimeoutError:
            return None

    async def edit(self, text, buttons=None, force=False, min_gap=2.5):
        """تحديث رسالة البوت (مع تحديد سرعة التحديث لتجنب FloodWait)."""
        if not (BOT and self.inline_id):
            return False
        now = time.monotonic()
        if not force and now - self._last_edit < min_gap:
            return False
        self._last_edit = now
        try:
            await BOT.edit_message(self.inline_id, text, buttons=buttons, link_preview=False)
            return True
        except errors.MessageNotModifiedError:
            return True
        except Exception as e:
            log.debug("تعذر تحديث رسالة inline: %s", e)
            return False

    def close(self):
        _PENDING.pop(self.token, None)


def create(owner_id, chat_id, kind, data=None):
    now = time.time()
    for t in [t for t, p in _PENDING.items() if now - p.created > 3600]:
        _PENDING.pop(t, None)
    p = Pending(owner_id, chat_id, kind, data)
    _PENDING[p.token] = p
    return p


def get(token):
    return _PENDING.get(token)


async def send_inline(client, chat_id, query, reply_to=None):
    """
    يرسل نتيجة inline من البوت الرئيسي عبر حساب المستخدم.
    يرجع (الرسالة, سبب_الفشل). لو فشل الرسالة = None والسبب نص عربي.
    """
    if not available():
        return None, "البوت الرئيسي غير متصل بهذي العملية."
    try:
        results = await client.inline_query(BOT_USERNAME, query, entity=chat_id)
        if not results:
            return None, "البوت ما رجّع نتيجة."
        msg = await results[0].click(chat_id, reply_to=reply_to)
        return msg, None
    except errors.BotInlineDisabledError:
        return None, "inline مو مفعّل: افتح @BotFather ← /setinline ← اختر البوت ← اكتب أي نص."
    except errors.BotResponseTimeoutError:
        return None, "البوت ما رد بالوقت (تأكد انه شغّال)."
    except Exception as e:
        return None, f"{e.__class__.__name__}: {str(e)[:80]}"
