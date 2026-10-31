"""افتارات ومحتوى عشوائي من قنوات عامة — جدول واحد، وكاش 30 دقيقة (سريع جداً بعد أول مرة)."""
import random

from telethon.tl import types as T

from core.framework import command

PHOTO, MEDIA, AUDIO, ANY = "photo", "media", "audio", "any"
# الأمر: (القناة، النوع، الوصف، الكلايشة)
SOURCES = {
    ".بنات": ("banaaaat1", PHOTO, "افتارات بنات", "🧚🏻‍♀️ **افتارات بنات**"),
    ".بنت_انمي": ("shhdhn", PHOTO, "افتارات بنات انمي", "🎌 **بنت انمي**"),
    ".ولد_انمي": ("dnndxn", PHOTO, "افتارات ولد انمي", "🎌 **ولد انمي**"),
    ".بيست": ("Tatkkkkkim", PHOTO, "بيست وتطقيمات", "💎 **بيست**"),
    ".رمادي": ("shababbbbR", PHOTO, "افتارات شباب رمادية", "🖤 **رمادي**"),
    ".رماديه": ("banatttR", PHOTO, "افتارات بنات رمادية", "🤍 **رمادية**"),
    ".ستوري_انمي": ("AA_Zll", MEDIA, "ستوريات انمي", "🌸 **ستوري انمي**"),
    ".ادت": ("snje1", MEDIA, "مقاطع ادت", "🎬 **ادت**"),
    ".رياكشن": ("reagshn", MEDIA, "ري اكشن (ردود متحركة)", "🎭 **ري اكشن**"),
    ".ري_اكشن": ("gafffg", MEDIA, "ري اكشن 2", "🎭 **ري اكشن**"),
    ".غنيلي": ("TEAMSUL", AUDIO, "اغنية عشوائية", "🎧 **غنيلي**"),
    ".رقيه": ("Rqy_1", AUDIO, "رقية شرعية", "🕋 **رقية شرعية**"),
    ".شعر": ("L1BBBL", ANY, "شعر عشوائي", "📜 **شعر**"),
    ".حالات": ("RSHDO5", ANY, "حالات واتس", "💬 **حالة**"),
    ".تويت": ("twit_selva", ANY, "تغريدات", "🐦 **تويتة**"),
    ".معلومه": ("A_l3l", ANY, "معلومة ثقافية", "📚 **معلومة**"),
}
_FILTERS = {PHOTO: T.InputMessagesFilterPhotos, MEDIA: T.InputMessagesFilterPhotoVideo, AUDIO: T.InputMessagesFilterMusic}


def _make(channel, kind, caption):
    async def handler(cmd):
        ctx = cmd.ctx
        pool = ctx.cached(("av", channel), 1800)
        if pool is None:
            await cmd.edit("⏳ **جاري التحميل...**")
            kw = {"filter": _FILTERS[kind]()} if kind in _FILTERS else {}
            msgs = await cmd.client.get_messages(channel, limit=150, **kw)
            pool = ctx.put_cache(("av", channel), [m for m in msgs if m and (m.media or m.text)])
        cmd.need(pool, "ما لقيت محتوى بهذي القناة حالياً (ممكن تغيّرت أو انحذفت).")
        pick = random.choice(pool)
        await cmd.client.send_file(cmd.chat_id, pick.media, caption=caption, reply_to=cmd.event.reply_to_msg_id) \
            if pick.media else await cmd.client.send_message(cmd.chat_id, f"{caption}\n\n{pick.text}", reply_to=cmd.event.reply_to_msg_id)
        await cmd.delete()
    return handler


for _n, (_ch, _kind, _desc, _cap) in SOURCES.items():
    command(_n, section="fun", desc=_desc)(_make(_ch, _kind, _cap))
