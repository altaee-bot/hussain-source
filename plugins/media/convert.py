"""تحويلات: ملصق ↔ صورة."""
import asyncio
import io
import os

from core.framework import command


def _to_png(path):
    from PIL import Image
    out = path.rsplit(".", 1)[0] + ".png"
    Image.open(path).convert("RGBA").save(out, "PNG")
    return out


def _to_webp(path):
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    img.thumbnail((512, 512))
    buf = io.BytesIO()
    img.save(buf, "WEBP")
    buf.seek(0)
    buf.name = "sticker.webp"
    return buf


@command(".تحويل", section="media", usage=".تحويل (بالرد على ملصق أو صورة)",
         desc="ملصق ← صورة PNG، وصورة ← ملصق")
async def convert(cmd):
    r = await cmd.reply_msg()
    cmd.need(r and (r.sticker or r.photo), "رد على ملصق أو صورة.")
    await cmd.edit("🔄 **جاري التحويل...**")
    path = await cmd.client.download_media(r)
    out = None
    try:
        if r.sticker:
            if (r.file.mime_type or "") not in ("image/webp",):
                cmd.fail("هذا الملصق متحرك — التحويل يدعم الملصقات الثابتة فقط.")
            out = await asyncio.to_thread(_to_png, path)
            await cmd.client.send_file(cmd.chat_id, out, reply_to=r.id, force_document=False)
        else:
            buf = await asyncio.to_thread(_to_webp, path)
            await cmd.client.send_file(cmd.chat_id, buf, reply_to=r.id)
        await cmd.delete()
    finally:
        for p in (path, out):
            if p and os.path.exists(p):
                os.remove(p)
