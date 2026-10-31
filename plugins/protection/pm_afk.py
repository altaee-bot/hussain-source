"""حماية الخاص (سماح/منع الغرباء) + وضع الغياب (سليب)."""
import time

from telethon import events

from core.framework import command, listener
from core.ui import human_dur


# ───────────────────────── حماية الخاص
def _pm(ctx):
    d = ctx.state.dict("pm_guard")
    d.setdefault("on", False)
    d.setdefault("allowed", [])
    d.setdefault("warns", {})
    d.setdefault("limit", 3)
    return d


@command(".حماية", section="protection", usage=".حماية تشغيل | ايقاف | حد <رقم>",
         desc="حماية الخاص: الغريب ياخذ تحذيرات ثم بلوك، إلا إذا سمحت له بـ `.سماح`")
async def pm_guard(cmd):
    g = _pm(cmd.ctx)
    w = cmd.words
    if w and w[0] in ("تشغيل", "تفعيل", "on"):
        g["on"] = True
    elif w and w[0] in ("ايقاف", "تعطيل", "off"):
        g["on"] = False
    elif w and w[0] == "حد" and cmd.int_arg(None, 1, 10):
        g["limit"] = cmd.int_arg(3, 1, 10)
    else:
        state = "شغّالة ✅" if g["on"] else "متوقفة ⛔"
        return await cmd.edit(f"🛡 **حماية الخاص:** {state}\n⚠️ عدد التحذيرات: `{g['limit']}`  |  ✅ المسموح لهم: `{len(g['allowed'])}`\n"
                              "`.حماية تشغيل` | `.حماية ايقاف` | `.حماية حد 3` | `.سماح` | `.منع_سماح`")
    cmd.ctx.save()
    await cmd.edit(f"🛡 حماية الخاص: {'**تم التشغيل** ✅' if g['on'] else '**تم الإيقاف** ⛔'}")


@command(".سماح", section="protection", scope="private", desc="السماح للشخص بمراسلتك (بالخاص)")
async def pm_allow(cmd):
    g = _pm(cmd.ctx)
    uid = cmd.chat_id
    if uid not in g["allowed"]:
        g["allowed"].append(uid)
    g["warns"].pop(str(uid), None)
    cmd.ctx.save()
    await cmd.edit("✅ **تم السماح له بمراسلتك.**")


@command(".منع_سماح", section="protection", scope="private", desc="سحب السماح عن الشخص")
async def pm_deny(cmd):
    g = _pm(cmd.ctx)
    if cmd.chat_id in g["allowed"]:
        g["allowed"].remove(cmd.chat_id)
        cmd.ctx.save()
    await cmd.edit("🚫 **تم سحب السماح.**")


@listener(events.NewMessage(outgoing=True, func=lambda e: e.is_private))
async def auto_allow(event, ctx):
    """لو انت راسلت شخص، نسمح له تلقائياً."""
    g = ctx.state.get("pm_guard")
    if g and g.get("on") and event.chat_id not in g["allowed"]:
        g["allowed"].append(event.chat_id)
        ctx.save()


@listener(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def pm_watch(event, ctx):
    g = ctx.state.get("pm_guard")
    if not g or not g.get("on") or event.sender_id in g["allowed"] or event.sender_id in ctx.helpers:
        return
    sender = await event.get_sender()
    if getattr(sender, "bot", False) or getattr(sender, "contact", False) or getattr(sender, "is_self", False) \
            or getattr(sender, "verified", False):
        return
    key = str(event.sender_id)
    n = g["warns"].get(key, 0) + 1
    g["warns"][key] = n
    ctx.save()
    limit = g.get("limit", 3)
    if n >= limit:
        from telethon import functions
        await event.reply("🚫 **تجاوزت عدد التحذيرات — تم حظرك.**")
        await ctx.client(functions.contacts.BlockRequest(id=event.sender_id))
        g["warns"].pop(key, None)
        ctx.save()
        return
    await event.reply(f"🛡 **نظام حماية الخاص**\nهذا الحساب محمي، ما أستلم رسائل من غير المسموح لهم.\n"
                      f"⚠️ **تحذير {n}/{limit}** — انتظر حتى يرد صاحب الحساب.")


# ───────────────────────── وضع الغياب
@command(".سليب", ".غياب", section="protection", usage=".سليب [السبب]",
         desc="وضع الغياب: أرد تلقائياً على من يراسلك أو يمنشنك، ويتوقف أول ما تكتب أي رسالة")
async def afk_on(cmd):
    cmd.ctx.state.data["afk"] = {"since": time.time(), "reason": cmd.args[:200]}
    cmd.ctx.save()
    await cmd.edit("😴 **تم تفعيل وضع الغياب.**" + (f"\n📝 السبب: {cmd.args}" if cmd.args else "")
                   + "\n🔙 يتوقف تلقائياً أول ما ترسل رسالة.")
    cmd.ctx.cache["afk_skip"] = cmd.event.id


@listener(events.NewMessage(outgoing=True))
async def afk_off(event, ctx):
    afk = ctx.state.get("afk")
    if not afk or ctx.cache.get("afk_skip") == event.id:
        return
    text = event.raw_text or ""
    if text.startswith(".سليب") or text.startswith(".غياب"):
        return
    ctx.state.data.pop("afk", None)
    ctx.save()
    away = human_dur(time.time() - afk["since"])
    msg = await ctx.client.send_message(event.chat_id, f"🔙 **رجعت!** كنت غايب `{away}`.")
    import asyncio
    await asyncio.sleep(5)
    await msg.delete()


@listener(events.NewMessage(incoming=True, func=lambda e: e.is_private or e.mentioned))
async def afk_reply(event, ctx):
    afk = ctx.state.get("afk")
    if not afk:
        return
    sender = await event.get_sender()
    if getattr(sender, "bot", False):
        return
    if not ctx.cooldown(("afk", event.chat_id), 180):
        return
    away = human_dur(time.time() - afk["since"])
    reason = f"\n📝 **السبب:** {afk['reason']}" if afk.get("reason") else ""
    await event.reply(f"😴 **صاحب الحساب غايب حالياً**\n⏱ **من:** `{away}`{reason}\n✉️ راح يرد عليك أول ما يرجع.")
