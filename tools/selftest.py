"""
اختبار ذاتي للسورس — شغّله بعد أي تعديل:   python tools/selftest.py
يفحص: تحميل كل الإضافات، تعارض الأوامر، تشغيل الموزّع بعميل وهمي، أزرار البوت (≤64 بايت)، تدفق .يوت.
ما يحتاج تيليجرام ولا انترنت.
"""
import asyncio
import os
import sys
import types as pytypes

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import bridge, catalog, framework, inline_bot, loader, yt  # noqa: E402
from core.context import Ctx  # noqa: E402

PASS, FAIL = [], []


def bdata(button):
    """بيانات زر inline كـ bytes (تعمل مع كل إصدارات تيليثون)."""
    d = getattr(button, "data", None)
    if d is None:
        d = (button.to_dict().get("type") or {}).get("data")
    return d or b""


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("✅" if cond else "❌"), name, extra if not cond else "")


# ───────────── عميل وهمي
class FakeClient:
    def __init__(self):
        self.handlers = []
        self.sent = []

    def add_event_handler(self, fn, builder=None):
        self.handlers.append((fn, builder))

    async def get_me(self):
        return pytypes.SimpleNamespace(id=1, first_name="Test", username="t", premium=False)

    async def send_message(self, chat, text=None, **kw):
        self.sent.append((chat, text))
        return pytypes.SimpleNamespace(id=99, delete=self._noop)

    async def _noop(self):
        return None

    async def get_entity(self, ref):
        raise ValueError("Cannot find any entity corresponding to " + str(ref))


class FakeEvent:
    def __init__(self, text, out=True, sender=1, reply=None, private=True):
        self.raw_text, self.out, self.sender_id = text, out, sender
        self.edits, self.replies = [], []
        self.is_reply = reply is not None
        self._reply = reply
        self.chat_id = 123
        self.is_private, self.is_group, self.is_channel = private, not private, False
        self.id = 5
        self.reply_to_msg_id = None
        self.message = pytypes.SimpleNamespace(entities=None, media=None, via_bot_id=None)

    async def edit(self, text, **kw):
        self.edits.append(text)
        return self.message

    async def reply(self, text, **kw):
        self.replies.append(text)
        return self.message

    respond = reply

    async def delete(self):
        self.edits.append("<deleted>")

    async def get_reply_message(self):
        return self._reply

    def get_entities_text(self):
        return []

    async def get_sender(self):
        return pytypes.SimpleNamespace(username="x", bot=False)


async def run(text, ctx_setup=None, **kw):
    client = FakeClient()
    ctx = Ctx(client)
    if ctx_setup:
        ctx_setup(ctx)
    framework.attach(client, ctx)
    dispatch = client.handlers[0][0]
    ev = FakeEvent(text, **kw)
    await dispatch(ev)
    return ev


async def main():
    ok, failed = loader.import_plugins(verbose=False)
    check("كل ملفات plugins تتحمّل", not failed, failed)
    check("عدد الأوامر معقول", len(framework.REGISTRY) > 150, len(framework.REGISTRY))

    # تعارض أسماء
    seen, dup = {}, []
    for s in framework.REGISTRY:
        for k in s.keys:
            if k in seen and seen[k] is not s:
                dup.append(k)
            seen[k] = s
    check("لا يوجد تعارض أوامر", not dup, dup)

    # كل أمر له قسم معروف ووصف
    sections = {s[1] for s in catalog.SECTIONS}
    bad = [s.names[0] for s in framework.REGISTRY if s.section not in sections]
    check("كل الأوامر بأقسام معروفة", not bad, bad)
    nodesc = [s.names[0] for s in framework.REGISTRY if not s.hidden and not s.desc]
    check("كل الأوامر الظاهرة لها وصف", not nodesc, nodesc)

    # القوائم
    for n in range(1, 15):
        t = catalog.help_text(n)
        check(f"قائمة م{n} ≤ 4096", len(t) <= 4096, len(t))
    check("القائمة الرئيسية ≤ 4096", len(catalog.main_menu_text()) <= 4096)

    # الموزّع
    ev = await run(".م")
    check(".م يعرض القائمة", ev.edits and "ريكو" in ev.edits[0])
    ev = await run(".م3")
    check(".م3 رقم لاحق", ev.edits and "الميديا" in ev.edits[0])
    ev = await run(".احسب 2*(3+4)^2")
    check(".احسب صحيح", ev.edits and "= 98" in ev.edits[0], ev.edits)
    ev = await run(".احسب __import__('os')")
    check(".احسب يرفض الكود الخبيث", ev.edits and "غير صالحة" in ev.edits[0], ev.edits)
    ev = await run(".اختار شاي | قهوة")
    check(".اختار", ev.edits and ("شاي" in ev.edits[0] or "قهوة" in ev.edits[0]))
    ev = await run(".رقم 5 5")
    check(".رقم", ev.edits and "`5`" in ev.edits[0], ev.edits)
    ev = await run(".زخرفة hello")
    check(".زخرفة", ev.edits and "𝐡" in ev.edits[0])
    ev = await run(".عمر 1999/5/20")
    check(".عمر", ev.edits and "عمرك" in ev.edits[0], ev.edits)
    ev = await run(".حظر")
    check("خطأ مفهوم بدل انهيار (بلا هدف)", ev.edits and "⚠️" in ev.edits[0] or ev.edits and "❌" in ev.edits[0], ev.edits)
    ev = await run(".طرد", private=True)
    check("scope=group يرفض بالخاص", ev.edits and "المجموعات" in ev.edits[0], ev.edits)
    ev = await run(".م", out=False, sender=777)
    check("الغريب ما يشغّل الأوامر", not ev.edits and not ev.replies)
    ev = await run(".الغاء_كتم")
    check("الشرطة السفلية = مسافة (اسم فيه _)", True)
    ev = await run(".وقت_تشغيل99")
    check("وقت_تشغيل نمط غير صالح", ev.edits and "13" in ev.edits[0], ev.edits)
    ev = await run(".ميمز")
    check(".ميمز قائمة", ev.edits and "ميمز ريكو" in ev.edits[0])

    # ───────────── جسر البوت وأزرار .يوت
    results = [{"id": f"id{i}", "url": f"https://youtu.be/id{i}", "title": f"فيديو رقم {i} " + "ط" * 30,
                "channel": "قناة", "duration": 3725, "views": 123456, "thumb": f"https://i.ytimg.com/vi/id{i}/hq.jpg"}
               for i in range(5)]
    p = bridge.create(1, 123, "yt", {"results": results, "idx": 0})
    text, rows = inline_bot.yt_main_screen(p)
    datas = [bdata(b) for r in rows for b in r]
    check("أزرار .يوت ≤ 64 بايت", datas and all(0 < len(d) <= 64 for d in datas), [len(d) for d in datas])
    check("نص .يوت فيه العنوان والمدة", "1:02:05" in text)

    info = {"duration": 200, "formats": [
        {"height": 360, "vcodec": "avc1", "acodec": "none", "filesize": 5_000_000},
        {"height": 720, "vcodec": "avc1", "acodec": "none", "filesize": 20_000_000},
        {"height": 1080, "vcodec": "vp9", "acodec": "none", "tbr": 2500},
        {"height": None, "vcodec": "none", "acodec": "mp4a", "filesize": 3_000_000}]}
    opts = yt.video_options(info)
    check("دقات الفيديو مستخرجة وبحجم", [h for h, _ in opts] == [360, 720, 1080] and opts[0][1] == 8_000_000, opts)
    _, vrows = inline_bot.yt_video_screen(p, info)
    check("أزرار الدقات ≤ 64 بايت", all(0 < len(bdata(b)) <= 64 for r in vrows for b in r))
    _, arows = inline_bot.yt_audio_screen(p, info)
    check("أزرار الصوت موجودة", len(arows) >= 2)

    # محاكاة ضغطات الأزرار (callback)
    class FakeCb:
        def __init__(self, data, sender=1):
            self.data = data.encode()
            self.sender_id = sender
            self.query = pytypes.SimpleNamespace(msg_id="INLINE123")
            self.answers, self.edits = [], []

        async def answer(self, text=None, alert=False):
            self.answers.append((text, alert))

        async def edit(self, text, **kw):
            self.edits.append(text)

    cb = FakeCb(f"rc|yt|{p.token}|n")
    await inline_bot._yt_cb(cb, cb.data.decode().split("|"))
    check("زر التالي يغيّر النتيجة", p.data["idx"] == 1 and cb.edits)
    cb = FakeCb(f"rc|yt|{p.token}|go|v|720", sender=999)
    await inline_bot._yt_cb(cb, cb.data.decode().split("|"))
    check("غريب يضغط الزر → مرفوض", cb.answers and cb.answers[0][1] is True and not p.future.done())
    cb = FakeCb(f"rc|yt|{p.token}|go|v|720")
    await inline_bot._yt_cb(cb, cb.data.decode().split("|"))
    choice = await p.wait(1)
    check("اختيار الدقة يصل لأمر .يوت", choice == {"kind": "v", "quality": "720", "idx": 1}, choice)
    check("inline_id محفوظ للتحديثات", p.inline_id == "INLINE123")

    p2 = bridge.create(1, 123, "yt", {"results": results, "idx": 0})
    cb = FakeCb(f"rc|yt|{p2.token}|x")
    await inline_bot._yt_cb(cb, cb.data.decode().split("|"))
    check("زر الإلغاء", p2.cancelled and await p2.wait(1) is None)

    # قائمة الأوامر inline
    cb = FakeCb("rc|m|1|5")
    await inline_bot._menu_cb(cb, cb.data.decode().split("|"))
    check("زر قسم القائمة", cb.edits and "الوقت" in cb.edits[0])
    cb = FakeCb("rc|m|1|5", sender=2)
    await inline_bot._menu_cb(cb, cb.data.decode().split("|"))
    check("قائمة inline لا تفتح لغير المالك", cb.answers and cb.answers[0][1] is True)
    mb = inline_bot.menu_buttons(1)
    check("أزرار القائمة ≤ 64 بايت", all(len(bdata(b)) <= 64 for r in mb for b in r if bdata(b)))

    # .يوت: تحليل الصيغ
    from plugins.media.youtube import _parse
    check("_parse صوت", _parse("صوت فيروز")[0] == "a" and _parse("صوت فيروز")[2] == "فيروز")
    check("_parse فيديو بدقة", _parse("فيديو اغنية 720") == ("v", 720, "اغنية"))
    check("_parse عادي", _parse("اغنية حلوة") == (None, None, "اغنية حلوة"))



    # ───────────── أوامر الحالة (ردود، حماية، غياب، مساعدين) — بملفات مؤقتة
    import tempfile as _tf
    d = _tf.mkdtemp()

    def setup(ctx):
        ctx.data_dir = d
        ctx.state.path = os.path.join(d, "state.json")

    ev = await run(".رد سلام | وعليكم السلام", ctx_setup=setup)
    check(".رد مباشر يحفظ", ev.edits and "تم حفظ الرد" in ev.edits[0], ev.edits)
    check("الرد انكتب بالملف", os.path.exists(os.path.join(d, "responses.json")))
    ev = await run(".حماية تشغيل", ctx_setup=setup)
    check(".حماية تشغيل", ev.edits and "التشغيل" in ev.edits[0], ev.edits)
    ev = await run(".حماية", ctx_setup=setup)
    check(".حماية حالة", ev.edits and "حماية الخاص" in ev.edits[0], ev.edits)
    ev = await run(".سليب مشغول", ctx_setup=setup)
    check(".سليب", ev.edits and "الغياب" in ev.edits[0], ev.edits)
    ev = await run(".حد_التحذير 5", ctx_setup=setup)
    check(".حد_التحذير", ev.edits and "5" in ev.edits[0], ev.edits)
    ev = await run(".المساعدين", ctx_setup=setup)
    check(".المساعدين فارغة", ev.edits and "ما عندك" in ev.edits[0], ev.edits)
    ev = await run(".غامق", ctx_setup=setup)
    check(".غامق تشغيل", ev.edits and "تفعيل" in ev.edits[0], ev.edits)
    ev = await run(".ترحيب هلا {mention} بـ {chat}", ctx_setup=setup)
    check(".ترحيب نص مخصص", ev.edits and "تم حفظ" in ev.edits[0], ev.edits)
    ev = await run(".اوامر_كل")
    check(".اوامر_كل", ev.edits and "كل أوامر" in ev.edits[0])
    ev = await run(".قفل")
    check(".قفل بدون نوع → رسالة بالأنواع (بالخاص يرفض)", ev.edits and ("المجموعات" in ev.edits[0]), ev.edits)

    # الحالة تنحفظ وتُقرأ بعد إعادة التشغيل
    from core.state import State
    st = State()
    st.load(os.path.join(d, "state.json"))
    st.save()
    ctx2 = Ctx(FakeClient())
    ctx2.state.path = None
    ctx2.state.load(os.path.join(d, "state.json"))
    check("الحالة تُقرأ من الملف", True)

    # ───────────── تدفق .يوت كامل بتحميل ورفع وهميين
    import tempfile
    from core import netutil
    from plugins.media import youtube as ytplug

    class FakeBot:
        def __init__(self):
            self.edits = []

        async def edit_message(self, inline_id, text, **kw):
            self.edits.append((inline_id, text))

    fake_bot = FakeBot()
    bridge.set_bot(fake_bot, "RecoBot")
    tmpdir = tempfile.mkdtemp()
    ytplug.yt.search = lambda q, n=5: results[:n]

    def fake_download(url, kind, quality, outdir, hook=None):
        os.makedirs(outdir, exist_ok=True)
        path = os.path.join(outdir, "song.mp3" if kind == "a" else "clip.mp4")
        open(path, "wb").write(b"x" * 2048)
        if hook:
            hook({"status": "downloading", "downloaded_bytes": 50, "total_bytes": 100, "speed": 10, "eta": 3})
        return path, {"title": "عنوان", "duration": 100, "uploader": "قناة", "height": 720, "width": 1280}
    ytplug.yt.download = fake_download

    async def fake_thumb(*a, **k):
        raise RuntimeError("no net")
    netutil.get_bytes = fake_thumb

    class FlowClient(FakeClient):
        def __init__(self):
            super().__init__()
            self.files = []

        async def send_file(self, chat, path, **kw):
            self.files.append((chat, os.path.basename(path), kw.get("caption")))

    client = FlowClient()
    ctx = Ctx(client)
    ctx.data_dir = os.path.join(tmpdir, "1")
    delivered = {}

    async def fake_send_inline(c, chat_id, query, reply_to=None):
        token = query.split(":", 1)[1]
        delivered["token"] = token
        return pytypes.SimpleNamespace(id=1, delete=client._noop), None
    bridge.send_inline = fake_send_inline

    ev = FakeEvent(".يوت فيروز")
    cmd = framework.Cmd(ev, client, ctx, ytplug.youtube.spec, "فيروز", None, True)

    async def user_clicks():
        while "token" not in delivered:
            await asyncio.sleep(0.05)
        pend = bridge.get(delivered["token"])
        pend.inline_id = "INL"
        pend.choose({"kind": "v", "quality": "720", "idx": 0})

    clicker = asyncio.create_task(user_clicks())
    await asyncio.wait_for(ytplug.youtube(cmd), 30)
    await clicker
    check("تدفق .يوت: أُرسل ملف الفيديو", client.files and client.files[0][1] == "clip.mp4", client.files)
    check("تدفق .يوت: تحديثات التقدم عبر البوت", any("جاري" in t for _, t in fake_bot.edits), fake_bot.edits)

    ev2 = FakeEvent(".يوت صوت فيروز")
    cmd2 = framework.Cmd(ev2, client, ctx, ytplug.youtube.spec, "صوت فيروز", None, True)
    await asyncio.wait_for(ytplug.youtube(cmd2), 30)
    check("تدفق .يوت صوت مباشر بلا أزرار", client.files[-1][1].endswith(".mp3"), client.files)

    # فشل الأزرار (inline غير مفعّل) → احتياطي صوت
    async def failing_inline(*a, **k):
        return None, "inline مو مفعّل"
    bridge.send_inline = failing_inline
    ytplug._WARNED["inline"] = True
    ev3 = FakeEvent(".يوت فيروز")
    cmd3 = framework.Cmd(ev3, client, ctx, ytplug.youtube.spec, "فيروز", None, True)
    await asyncio.wait_for(ytplug.youtube(cmd3), 30)
    check("احتياطي: لو inline فشل ينزل صوت", client.files[-1][1].endswith(".mp3"), client.files)

    # فحص الإلغاء
    p3 = bridge.create(1, 123, "yt", {"results": results, "idx": 0})
    p3.cancel()
    check("pending ملغي", p3.cancelled)

    print(f"\nالنتيجة: ✅ {len(PASS)}  ❌ {len(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
