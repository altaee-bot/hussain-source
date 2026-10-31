"""
user_core.py — تشغيل جلسة حساب واحد.

  1) يبني الـ client والـ ctx (حالة الحساب)
  2) يحمّل الأوامر من plugins/ عبر core.loader (موزّع واحد لكل حساب)
  3) يجهّز مجموعات التخزين (مرة وحدة، ويحفظ معرفاتها) وينتظر الأحداث

أخطاء الجلسة (AuthKey/محذوف/منتهي) تُرمى للأعلى ليقرر app.py؛ أخطاء الشبكة تُعاد محاولتها هناك.
"""
import asyncio
import logging
import os

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import CreateChatRequest, EditChatPhotoRequest, ImportChatInviteRequest
from telethon.tl.types import InputChatUploadedPhoto

from core import framework
from core.constants import SOURCE_CH
from core.context import Ctx
from core.loader import load_plugins

log = logging.getLogger("reco")

STORAGES = [
    # (مفتاح الحالة، اسم المجموعة، صورة، وصف)
    ("storage_pv", "RECO PV STORAGE", "ka.jpg",
     "✅ تم تعيين صورة التخزين الخاص بنجاح\n📂 RECO PV STORAGE\nهذه المجموعة مخصصة لتخزين رسائل الخاص والميديا ذاتية التدمير."),
    ("storage_groups", "RECO GROUPS STORAGE", "am.jpg",
     "✅ تم تعيين صورة تخزين المجموعات بنجاح\n👥 RECO GROUPS STORAGE\nهذه المجموعة مخصصة لتخزين رسائل المجموعات."),
    ("storage_deleted", "RECO DELETED STORAGE", "ma.jpg",
     "✅ تم تعيين صورة أرشيف المحذوفات بنجاح\n🗑 RECO DELETED STORAGE\nهنا يتم حفظ أي رسالة يتم حذفها."),
]


async def _find_dialog(client, title):
    async for d in client.iter_dialogs(limit=None):
        if d.name == title:
            return d.id
    return None


async def create_storage_group(client, title, photo_file, description):
    try:
        r = await client(CreateChatRequest(title=title, users=["me"]))
        chats = getattr(r, "chats", None) or getattr(getattr(r, "updates", None), "chats", None)
        chat_id = chats[0].id if chats else None
        if not chat_id:
            await asyncio.sleep(3)
            chat_id = await _find_dialog(client, title)
        if chat_id:
            await asyncio.sleep(2)
            if os.path.exists(photo_file):
                up = await client.upload_file(photo_file)
                await client(EditChatPhotoRequest(chat_id=chat_id, photo=InputChatUploadedPhoto(up)))
            await client.send_message(chat_id, description)
        return chat_id
    except Exception as e:
        log.warning("❌ خطأ إنشاء المجموعة %s: %s", title, e)
        return None


async def setup_storages(client, ctx):
    """يجلب معرفات مجموعات التخزين من الحالة المحفوظة؛ ينشئ الناقص فقط (قبل كانت تتكرر كل إقلاع لو الحساب عنده +100 محادثة)."""
    for target in (SOURCE_CH,):
        try:
            await client(JoinChannelRequest(target))
        except Exception:
            pass
    try:
        await client(ImportChatInviteRequest(hash="MenQ6rARNGtlMjli"))
    except Exception:
        pass
    saved = ctx.state.dict("storages")
    for key, title, photo, desc in STORAGES:
        chat_id = saved.get(key)
        if chat_id:
            try:
                await client.get_input_entity(chat_id)
            except Exception:
                chat_id = None
        if not chat_id:
            chat_id = await _find_dialog(client, title)
        if not chat_id:
            chat_id = await create_storage_group(client, title, photo, desc)
        if chat_id:
            saved[key] = chat_id
        setattr(ctx, key, chat_id)
    ctx.save()


async def start_user_source(session_str, api_id, api_hash, install_info=None):
    """يشغّل الحساب حتى ينقطع. يرمي الاستثناءات للمشرف (app.run_user_safely)."""
    client = TelegramClient(StringSession(session_str), api_id, api_hash,
                            connection_retries=None, retry_delay=3, auto_reconnect=True,
                            request_retries=5, flood_sleep_threshold=30)
    ctx = Ctx(client, install_info)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            from telethon.errors import AuthKeyUnregisteredError
            raise AuthKeyUnregisteredError(request=None)
        await ctx.load_state()
        load_plugins(client, ctx)
        await framework.run_starters(ctx)
        await setup_storages(client, ctx)
        me = await ctx.get_me()
        log.info("✅ سورس ريكو يعمل للحساب %s (%s)", me.first_name, me.id)
        await client.run_until_disconnected()
    finally:
        ctx.state.save()
        for t in (ctx.time_task, *ctx.hunting_tasks.values(), *ctx.auto_tasks.values(), *ctx.group_publish["tasks"].values()):
            if isinstance(t, asyncio.Task):
                t.cancel()
        await client.disconnect()
        log.info("📴 تم إغلاق جلسة المستخدم.")
