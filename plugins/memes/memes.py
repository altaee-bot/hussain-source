"""
الميمز والصوتيات: كل ميم أمر مستقل (مثل `.اسكت`) — بيانات كلها بملف memes.json
لإضافة ميم جديد: أضف سطر بـ memes.json  "اسم الميم": {"url": "https://t.me/القناة/رقم_الرسالة"}  وخلاص.
"""
import json
import os
import random
import re

from core import catalog
from core.framework import command
from core.ui import LINE

_HERE = os.path.dirname(os.path.abspath(__file__))
_T_ME = re.compile(r"t\.me/([A-Za-z]\w+)/(\d+)")


def _load():
    try:
        with open(os.path.join(_HERE, "memes.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ تعذر قراءة memes.json: {e}")
        return {}


MEMES = _load()


async def _send_meme(cmd, name):
    item = MEMES[name]
    url, cap = item["url"], item.get("caption", "")
    ctx, client = cmd.ctx, cmd.client
    reply_to = cmd.event.reply_to_msg_id
    file = ctx.cached(("meme", url), 3600)
    if file is None:
        m = _T_ME.search(url)
        if m:
            try:
                msg = await client.get_messages(m.group(1), ids=int(m.group(2)))
                file = msg.media if msg and msg.media else url
            except Exception:
                file = url
        else:
            file = url
        ctx.put_cache(("meme", url), file)
    await client.send_file(cmd.chat_id, file, caption=cap, reply_to=reply_to)
    await cmd.delete()


def _make(name):
    async def handler(cmd):
        await _send_meme(cmd, name)
    handler.__name__ = f"meme_{abs(hash(name))}"
    return handler


for _name in MEMES:
    command("." + _name, section="memes", desc=f"ميم: {_name}", hidden=True)(_make(_name))


def _names_lines():
    names = sorted(MEMES)
    return ["🔊 **الميمز المتوفرة** (اكتب `.` قبل الاسم):", "  ".join(f"`{n}`" for n in names)]


catalog.EXTRA_LINES["memes"] = _names_lines


@command(".ميمز", ".قائمة_الميمز", section="memes", desc="عرض كل الميمز المتوفرة")
async def meme_list(cmd):
    names = sorted(MEMES)
    await cmd.edit(f"**🔊 ميمز ريكو ({len(names)})**\n{LINE}\n" + "  ".join(f"`.{n}`" for n in names)
                   + f"\n{LINE}\n🎲 عشوائي: `.ميم`   🔎 بحث: `.ميم كلمة`")


@command(".ميم", section="memes", usage=".ميم [كلمة بحث]", desc="ميم عشوائي، أو أول ميم يحتوي كلمة البحث")
async def meme_random(cmd):
    q = cmd.args.strip()
    pool = [n for n in MEMES if q in n] if q else list(MEMES)
    cmd.need(pool, "ما لقيت ميم بهذا الاسم. شوف القائمة بـ `.ميمز`")
    await _send_meme(cmd, random.choice(pool))
