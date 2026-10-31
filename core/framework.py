"""
إطار أوامر ريكو
================
بدل ما كل أمر يسجّل handler بـ regex خاص به (800 handler يفحصون كل رسالة)،
هنا **موزّع واحد** لكل حساب: يشوف أول كلمة بالرسالة ويقفز مباشرة للأمر (O(1)).
الرسائل الواردة من الغرباء تُرفض بأول سطر — فالسورس يبقى خفيف حتى بالمجموعات الضخمة.

كتابة أمر جديد (بأي ملف داخل plugins/):

    from core.framework import command

    @command(".هلو", section="fun", desc="يسلم عليك", usage=".هلو [اسم]")
    async def hello(cmd):
        await cmd.edit(f"هلا بيك {cmd.args or 'يا غالي'} 👋")

ملاحظات:
- `.الغاء_حظر` و `.الغاء حظر` نفس الشي (الشرطة السفلية = مسافة).
- cmd.args = النص بعد الأمر، cmd.target() = الشخص (رد / @يوزر / ايدي).
- أي خطأ داخل الأمر ينعرض للمستخدم بشكل مفهوم وما يوقّف باقي الأوامر.
"""
import asyncio
import itertools
import logging
import re
from dataclasses import dataclass, field

from telethon import errors, events
from telethon.tl import types

from core.constants import PREFIX

log = logging.getLogger("reco")

from collections import Counter
USAGE = Counter()   # عدد استخدام كل أمر (للإحصائيات)
REGISTRY = []    # كل الأوامر (ثابتة لكل الحسابات)
LISTENERS = []   # مستمعات تلقائية (ترحيب، حفظ ميديا ...)
STARTERS = []    # دوال تشتغل مرة عند بدء كل حساب


class CmdError(Exception):
    """خطأ يُعرض للمستخدم كما هو (رسالة عربية مفهومة)."""


@dataclass(eq=False)
class CommandSpec:
    names: tuple
    section: str
    desc: str
    usage: str
    helpers: bool
    scope: str            # any | group | private
    hidden: bool
    numeric_suffix: bool
    anyone: bool
    func: object = None
    module: str = ""
    keys: tuple = field(default_factory=tuple)


@dataclass(eq=False)
class ListenerSpec:
    builder: object
    func: object
    module: str = ""


def _norm(name):
    return re.sub(r"[\s_]+", " ", name.strip())


def command(*names, section="tools", desc="", usage="", helpers=False, scope="any",
            hidden=False, numeric_suffix=False, anyone=False):
    """تسجيل أمر. الاسم الأول هو الأساسي والباقي مرادفات."""
    if not names:
        raise ValueError("لازم اسم أمر واحد على الأقل")

    def deco(fn):
        for n in names:
            if not n.startswith(PREFIX):
                raise ValueError(f"الأمر يجب أن يبدأ بـ {PREFIX}: {n}")
        spec = CommandSpec(
            names=tuple(names), section=section, desc=desc or (fn.__doc__ or "").strip().split("\n")[0],
            usage=usage, helpers=helpers, scope=scope, hidden=hidden,
            numeric_suffix=numeric_suffix, anyone=anyone, func=fn, module=fn.__module__,
            keys=tuple(_norm(n) for n in names))
        REGISTRY.append(spec)
        fn.spec = spec
        return fn
    return deco


def listener(builder, *, hidden=True):
    """مستمع لحدث تيليجرام. الدالة تستلم (event, ctx)."""
    def deco(fn):
        LISTENERS.append(ListenerSpec(builder, fn, fn.__module__))
        return fn
    return deco


def on_start(fn):
    """دالة (async) تشتغل مرة عند بدء كل حساب: fn(ctx)."""
    STARTERS.append(fn)
    return fn


# ───────────────────────── أخطاء مفهومة
def _e(name):
    return getattr(errors, name, None)


_FRIENDLY = [
    ("ChatAdminRequiredError", "أحتاج صلاحيات أدمن بهذي الدردشة."),
    ("ChatAdminInviteRequiredError", "أحتاج صلاحية دعوة المستخدمين."),
    ("UserAdminInvalidError", "ما أكدر أنفذها على هذا الشخص (أدمن أو مالك)."),
    ("UserNotParticipantError", "هذا الشخص مو موجود بالدردشة."),
    ("ChatWriteForbiddenError", "ما عندي صلاحية الكتابة هنا."),
    ("UserPrivacyRestrictedError", "إعدادات خصوصية الشخص تمنع هذا الإجراء."),
    ("UserIsBlockedError", "هذا المستخدم حاظرك."),
    ("UsernameNotOccupiedError", "هذا اليوزر غير موجود."),
    ("UsernameInvalidError", "صيغة اليوزر غير صحيحة."),
    ("PeerIdInvalidError", "ما لقيت هذا الحساب."),
    ("MessageIdInvalidError", "رقم الرسالة غير صحيح أو انحذفت."),
    ("ChannelPrivateError", "القناة خاصة وأنت مو عضو فيها."),
    ("BotInlineDisabledError", "وضع inline مو مفعّل للبوت (فعّله من @BotFather بالأمر /setinline)."),
    ("MessageTooLongError", "النص طويل جداً."),
    ("PhotoInvalidError", "الصورة غير صالحة."),
]


def friendly_error(exc):
    if isinstance(exc, errors.FloodWaitError):
        return f"تيليجرام طلب الانتظار **{exc.seconds}** ثانية قبل المحاولة مرة ثانية."
    for name, msg in _FRIENDLY:
        cls = _e(name)
        if cls and isinstance(exc, cls):
            return msg
    if isinstance(exc, (ValueError, TypeError)) and "entity" in str(exc).lower():
        return "ما لقيت هذا الحساب/الدردشة — تأكد من اليوزر أو الايدي."
    if isinstance(exc, asyncio.TimeoutError):
        return "انتهى الوقت بدون رد."
    name = exc.__class__.__name__
    return f"خطأ غير متوقع: `{name}` — `{str(exc)[:120]}`"


def _chunks(text, size=4000):
    if len(text) <= size:
        return [text]
    parts, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > size:
            parts.append(cur)
            cur = ""
        cur += line + "\n"
    if cur.strip():
        parts.append(cur)
    return parts


# ───────────────────────── كائن الأمر
_ID_RE = re.compile(r"^(?:@[A-Za-z]\w{3,31}|-?\d{5,15}|(?:https?://)?t\.me/[A-Za-z]\w{3,31})$")


class Cmd:
    __slots__ = ("event", "client", "ctx", "spec", "args", "suffix", "is_owner", "_reply", "_reply_done", "rest")

    def __init__(self, event, client, ctx, spec, args, suffix, is_owner):
        self.event, self.client, self.ctx, self.spec = event, client, ctx, spec
        self.args, self.suffix, self.is_owner = args, suffix, is_owner
        self._reply, self._reply_done = None, False
        self.rest = args

    # ── معلومات سريعة
    @property
    def chat_id(self):
        return self.event.chat_id

    @property
    def words(self):
        return self.args.split()

    @property
    def in_group(self):
        return bool(self.event.is_group or self.event.is_channel)

    # ── ردود
    async def edit(self, text, **kw):
        """المالك: يعدّل رسالته. المساعد: يرد. أي نص طويل يتقسم تلقائياً."""
        parts = _chunks(str(text))
        first = parts[0]
        msg = None
        if self.is_owner:
            try:
                msg = await self.event.edit(first, **kw)
            except errors.MessageNotModifiedError:
                msg = self.event.message
            except Exception:
                msg = None
        if msg is None:
            msg = await (self.event.respond(first, **kw) if self.is_owner else self.event.reply(first, **kw))
        for extra in parts[1:]:
            await self.event.respond(extra)
        return msg

    async def reply(self, text, **kw):
        return await self.event.reply(text, **kw)

    async def send(self, *a, **kw):
        return await self.client.send_message(self.event.chat_id, *a, **kw)

    async def delete(self):
        try:
            await self.event.delete()
        except Exception:
            pass

    def fail(self, text):
        raise CmdError(text)

    def need(self, cond, text):
        if not cond:
            raise CmdError(text)

    # ── رسالة الرد
    async def reply_msg(self):
        if not self._reply_done:
            self._reply_done = True
            if self.event.is_reply:
                try:
                    self._reply = await self.event.get_reply_message()
                except Exception:
                    self._reply = None
        return self._reply

    # ── تحديد الشخص: رد > منشن > @يوزر/ايدي
    async def target(self, required=True, allow_self=True):
        user = None
        r = await self.reply_msg()
        tokens = self.args.split()
        if r is not None and r.sender_id and not (tokens and _ID_RE.match(tokens[0])):
            user = await self._entity(r.sender_id)
        else:
            try:
                for ent, txt in self.event.get_entities_text():
                    if isinstance(ent, types.MessageEntityMentionName):
                        user = await self._entity(ent.user_id)
                        break
            except Exception:
                pass
            if user is None and tokens and _ID_RE.match(tokens[0]):
                tok = tokens[0]
                try:
                    user = await self._entity(int(tok) if re.fullmatch(r"-?\d+", tok) else tok)
                except Exception:
                    user = None
                self.rest = self.args.split(None, 1)[1] if len(tokens) > 1 else ""
        if user is None:
            if required:
                raise CmdError("رد على رسالة الشخص أو اكتب معرفه `@يوزر` أو ايديه.")
            return None
        if not allow_self:
            me = await self.ctx.get_me()
            if user.id == me.id:
                raise CmdError("ما تكدر تطبق هذا الأمر على نفسك.")
        return user

    async def _entity(self, ref):
        return await self.client.get_entity(ref)

    def int_arg(self, default=None, lo=None, hi=None):
        for w in self.words:
            if re.fullmatch(r"\d+", w):
                v = int(w)
                if lo is not None:
                    v = max(lo, v)
                if hi is not None:
                    v = min(hi, v)
                return v
        return default


# ───────────────────────── الموزّع
_TOK = re.compile(r"\S+")


def build_table():
    table, longest = {}, 1
    for spec in REGISTRY:
        for key in spec.keys:
            old = table.get(key)
            if old is not None and old is not spec:
                log.warning("⚠️ تعارض أمر %s بين %s و %s", key, old.module, spec.module)
            table[key] = spec
            longest = max(longest, key.count(" ") + 1)
    return table, min(longest, 3)


def attach(client, ctx):
    """يربط موزّع الأوامر والمستمعات بحساب واحد."""
    table, longest = build_table()
    anyone_heads = {k.split(" ")[0] for s in REGISTRY if s.anyone for k in s.keys}
    suffix_specs = {k: s for s in REGISTRY if s.numeric_suffix for k in s.keys}

    async def dispatch(event):
        text = event.raw_text
        if not text or text[0] != PREFIX or len(text) < 2:
            return
        out = event.out
        helper = False
        if not out:
            helper = event.sender_id in ctx.helpers
            if not helper and _norm(text.split(None, 1)[0]).split(" ")[0] not in anyone_heads:
                return
        toks = list(itertools.islice(_TOK.finditer(text), longest))
        if not toks:
            return
        spec, used, suffix = None, 0, None
        for n in range(len(toks), 0, -1):
            key = _norm(" ".join(t.group() for t in toks[:n]))
            spec = table.get(key)
            if spec:
                used = n
                break
        if spec is None:
            m = re.fullmatch(r"(\.\D+?)(\d+)", toks[0].group())
            if m:
                cand = suffix_specs.get(_norm(m.group(1)))
                if cand:
                    spec, used, suffix = cand, 1, m.group(2)
        if spec is None:
            return
        if not out and not spec.anyone and not (helper and spec.helpers):
            return
        args = text[toks[used - 1].end():].strip()
        cmd = Cmd(event, client, ctx, spec, args, suffix, out)
        if spec.scope == "group" and not cmd.in_group:
            return await _notify(cmd, "⚠️ هذا الأمر يعمل داخل المجموعات والقنوات فقط.")
        if spec.scope == "private" and not event.is_private:
            return await _notify(cmd, "⚠️ هذا الأمر يعمل بالخاص فقط.")
        USAGE[spec.names[0]] += 1
        try:
            await spec.func(cmd)
        except CmdError as e:
            await _notify(cmd, f"⚠️ {e}")
        except errors.MessageNotModifiedError:
            pass
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.exception("❌ خطأ بالأمر %s", spec.names[0])
            await _notify(cmd, f"❌ {friendly_error(e)}")

    client.add_event_handler(dispatch, events.NewMessage())

    def wrap(fn):
        async def handler(event):
            try:
                await fn(event, ctx)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("❌ خطأ بمستمع %s", getattr(fn, "__name__", fn))
        return handler

    for ls in LISTENERS:
        client.add_event_handler(wrap(ls.func), ls.builder)
    return table


async def run_starters(ctx):
    for fn in STARTERS:
        try:
            await fn(ctx)
        except Exception:
            log.exception("❌ خطأ ببدء %s", getattr(fn, "__name__", fn))


async def _notify(cmd, text):
    try:
        await cmd.edit(text)
    except Exception:
        pass
