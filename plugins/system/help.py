"""القوائم: .م / .م1 … .م14 / .اوامر (أزرار) / .اوامر_كل — كلها تتولّد تلقائياً من الكتالوج."""
from core import bridge, catalog
from core.framework import command


@command(".م", ".الاوامر", section="system", numeric_suffix=True, usage=".م  |  .م<رقم>",
         desc="القائمة الرئيسية، أو قسم معيّن مثل `.م3`")
async def sections(cmd):
    if cmd.suffix:
        return await cmd.edit(catalog.help_text(int(cmd.suffix), limit=100000))
    await cmd.edit(catalog.main_menu_text())


@command(".اوامر", section="system", desc="قائمة الأوامر بأزرار شفافة (تحتاج inline مفعّل بالبوت)")
async def menu(cmd):
    me = await cmd.ctx.get_me()
    if bridge.available():
        msg, why = await bridge.send_inline(cmd.client, cmd.chat_id, f"menu:{me.id}",
                                            reply_to=cmd.event.reply_to_msg_id)
        if msg is not None:
            return await cmd.delete()
        await cmd.edit(f"⚠️ تعذر عرض الأزرار: {why}\n\n{catalog.main_menu_text()}")
        return
    await cmd.edit(catalog.main_menu_text())


@command(".اوامر_كل", section="system", desc="كل الأوامر بقائمة مختصرة")
async def all_cmds(cmd):
    await cmd.edit(catalog.all_commands_text())
