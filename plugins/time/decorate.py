"""الزخرفة: .زخرفة <نص> — يعطيك عدة أشكال جاهزة للنسخ (إنجليزي وعربي)."""
from core.framework import command
from core.ui import LINE


def _shift(start_upper, start_lower, start_digit=None):
    m = {}
    for i in range(26):
        m[chr(65 + i)] = chr(start_upper + i)
        m[chr(97 + i)] = chr(start_lower + i)
    if start_digit:
        for i in range(10):
            m[str(i)] = chr(start_digit + i)
    return m


LATIN = {
    "𝐁𝐨𝐥𝐝": _shift(0x1D400, 0x1D41A, 0x1D7CE),
    "𝘐𝘵𝘢𝘭𝘪𝘤": _shift(0x1D608, 0x1D622, 0x1D7E2),
    "𝙱𝚘𝚕𝚍 𝙸𝚝𝚊𝚕𝚒𝚌": _shift(0x1D63C, 0x1D656, 0x1D7EC),
    "𝓢𝓬𝓻𝓲𝓹𝓽": _shift(0x1D4D0, 0x1D4EA),
    "𝕱𝖗𝖆𝖐𝖙𝖚𝖗": _shift(0x1D56C, 0x1D586),
    "𝗦𝗮𝗻𝘀": _shift(0x1D5D4, 0x1D5EE, 0x1D7EC),
    "𝙼𝚘𝚗𝚘": _shift(0x1D670, 0x1D68A, 0x1D7F6),
    "Ⓒⓘⓡⓒⓛⓔ": {**_shift(0x24B6, 0x24D0), **{str(i): chr(0x2460 + i - 1) for i in range(1, 10)}, "0": "⓪"},
    "Ｗｉｄｅ": _shift(0xFF21, 0xFF41, 0xFF10),
}
SMALLCAPS = dict(zip("abcdefghijklmnopqrstuvwxyz", "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"))
# حروف عربية لا تتصل بما بعدها (ما نضيف بعدها تطويل)
_NON_JOIN = set("اأإآدذرزوؤةىء ")


def _tatweel(text):
    out = []
    for i, ch in enumerate(text):
        out.append(ch)
        nxt = text[i + 1] if i + 1 < len(text) else " "
        if ch not in _NON_JOIN and "\u0621" <= ch <= "\u064A" and "\u0621" <= nxt <= "\u064A":
            out.append("ـ")
    return "".join(out)


def _arabic_styles(t):
    tt = _tatweel(t)
    return [tt, f"꧁༺ {tt} ༻꧂", f"★彡 {tt} 彡★", f"•°¯`•• {tt} ••´¯°•", f"『 {tt} 』", f"✦•┈┈┈ {tt} ┈┈┈•✦",
            f"⌯ {tt} ⌯", f"❝ {tt} ❞", f"【 {tt} 】", f"༺ {tt} ༻"]


@command(".زخرفة", ".زغرفة", section="time", usage=".زخرفة <نص>", desc="زخرفة النص بأشكال كثيرة (عربي/إنجليزي) جاهزة للنسخ")
async def decorate(cmd):
    text = cmd.args
    if not text:
        r = await cmd.reply_msg()
        text = (r.raw_text if r else "") or ""
    cmd.need(text, "اكتب النص بعد الأمر أو رد على رسالة.")
    text = text[:60]
    rows = []
    if any("a" <= c.lower() <= "z" or c.isdigit() for c in text):
        for name, m in LATIN.items():
            rows.append(f"`{''.join(m.get(c, c) for c in text)}`")
        rows.append(f"`{''.join(SMALLCAPS.get(c.lower(), c) for c in text)}`")
    if any("\u0600" <= c <= "\u06FF" for c in text):
        rows += [f"`{s}`" for s in _arabic_styles(text)]
    if not rows:
        rows = [f"`{s}`" for s in _arabic_styles(text)]
    await cmd.edit(f"**🎨 زخرفة النص:**\n{LINE}\n" + "\n".join(rows) + f"\n{LINE}\n💡 اضغط على أي شكل لنسخه.")
