"""أوامر الحساب: ايدي، انتحال، تغيير الاسم والبايو والصورة، الخط الغامق."""
import os

from telethon import events, functions

from core.framework import CmdError, command, listener
from core.ui import card, kv, mention


@command(".ايدي", section="account", usage=".ايدي [رد/@يوزر]", desc="كشف معلومات حسابك أو الشخص المردود عليه")
async def ident(cmd):
    user = await cmd.target(required=False)
    if user is None:
        user = await cmd.ctx.get_me(refresh=True)
    rows = [kv("الاسم", mention(user), "👤"), kv("الايدي", f"`{user.id}`", "🆔"),
            kv("المعرف", f"@{user.username}" if getattr(user, "username", None) else "لا يوجد", "✨")]
    if getattr(user, "premium", False):
        rows.append(kv("بريميوم", "نعم ⭐", "💎"))
    if getattr(user, "bot", False):
        rows.append(kv("النوع", "بوت", "🤖"))
    if cmd.in_group:
        rows.append(kv("ايدي الدردشة", f"`{cmd.chat_id}`", "💬"))
    await cmd.edit(card("معلومات الحساب", rows))


@command(".معلوماتي", section="account", desc="تفاصيل حسابك (عدد الدردشات، الكروبات، القنوات)")
async def myinfo(cmd):
    await cmd.edit("⏳ **أجمع المعلومات...**")
    me = await cmd.ctx.get_me(refresh=True)
    privates = groups = channels = bots = 0
    async for d in cmd.client.iter_dialogs(limit=None):
        if d.is_user:
            if getattr(d.entity, "bot", False):
                bots += 1
            else:
                privates += 1
        elif d.is_group:
            groups += 1
        elif d.is_channel:
            channels += 1
    photos = await cmd.client.get_profile_photos("me", limit=0)
    await cmd.edit(card("معلوماتي", [
        kv("الاسم", mention(me), "👤"), kv("الايدي", f"`{me.id}`", "🆔"),
        kv("المعرف", f"@{me.username}" if me.username else "لا يوجد", "✨"),
        kv("الصور", f"`{photos.total}`", "🖼"), kv("محادثات خاصة", f"`{privates}`", "💬"),
        kv("مجموعات", f"`{groups}`", "👥"), kv("قنوات", f"`{channels}`", "📢"), kv("بوتات", f"`{bots}`", "🤖")]))


# ───────────────────────── الانتحال
def _orig_photo_path(ctx):
    return os.path.join(ctx.data_dir, "orig_photo.jpg")


@command(".انتحال", section="account", usage=".انتحال [رد/@يوزر]",
         desc="نسخ حساب شخص (اسم، بايو، صورة) — وتبقى بياناتك الأصلية محفوظة حتى بعد إعادة التشغيل")
async def impersonate(cmd):
    user = await cmd.target(allow_self=False)
    ctx, client = cmd.ctx, cmd.client
    await cmd.edit("⏳ **جاري نسخ الحساب...**")
    saved = ctx.state.dict("orig_profile")
    if not saved:
        me = await ctx.get_me(refresh=True)
        full = await client(functions.users.GetFullUserRequest("me"))
        saved.update({"first_name": me.first_name or "", "last_name": me.last_name or "",
                      "about": full.full_user.about or ""})
        photos = await client.get_profile_photos("me", limit=1)
        if photos:
            await client.download_media(photos[0], file=_orig_photo_path(ctx))
            saved["photo"] = True
        ctx.save()
    full_u = await client(functions.users.GetFullUserRequest(user.id))
    about = (full_u.full_user.about or "")[:70]
    await client(functions.account.UpdateProfileRequest(
        first_name=user.first_name or "", last_name=user.last_name or "", about=about))
    photos = await client.get_profile_photos(user.id, limit=1)
    if photos:
        path = await client.download_media(photos[0])
        try:
            up = await client.upload_file(path)
            await client(functions.photos.UploadProfilePhotoRequest(file=up))
        finally:
            if path and os.path.exists(path):
                os.remove(path)
    await ctx.get_me(refresh=True)
    await cmd.edit(card("تم الانتحال", [kv("الاسم", f"{user.first_name or ''} {user.last_name or ''}".strip(), "👤"),
                                         kv("البايو", about or "—", "📝"), "↩️ للرجوع: `.ايقاف_انتحال`"], icon="🎭"))


@command(".ايقاف_انتحال", section="account", desc="الرجوع لبياناتك الأصلية")
async def stop_impersonate(cmd):
    ctx, client = cmd.ctx, cmd.client
    saved = ctx.state.dict("orig_profile")
    if not saved:
        raise CmdError("ما عندي بيانات أصلية محفوظة — لم تنتحل أحداً.")
    await cmd.edit("🔄 **جاري استعادة هويتك الأصلية...**")
    await client(functions.account.UpdateProfileRequest(
        first_name=saved.get("first_name", ""), last_name=saved.get("last_name", ""), about=saved.get("about", "")))
    path = _orig_photo_path(ctx)
    if saved.get("photo") and os.path.exists(path):
        up = await client.upload_file(path)
        await client(functions.photos.UploadProfilePhotoRequest(file=up))
        os.remove(path)
    ctx.state.data["orig_profile"] = {}
    ctx.save()
    await ctx.get_me(refresh=True)
    await cmd.edit("✅ **رجعت لحسابك الطبيعي.**")


# ───────────────────────── تعديل الحساب
@command(".اسمي", ".ضع_اسم", section="account", usage=".اسمي <الاسم الجديد>", desc="تغيير اسمك")
async def set_name(cmd):
    cmd.need(cmd.args, "اكتب الاسم الجديد بعد الأمر.")
    first, _, last = cmd.args.partition("|")
    await cmd.client(functions.account.UpdateProfileRequest(first_name=first.strip()[:64], last_name=last.strip()[:64]))
    await cmd.ctx.get_me(refresh=True)
    await cmd.edit(f"✅ **تم تغيير الاسم إلى:** `{cmd.args}`\n💡 للاسم والكنية: `.اسمي الاسم | الكنية`")


@command(".بايو", ".ضع_بايو", section="account", usage=".بايو <النص>", desc="تغيير البايو (حتى 70 حرف)")
async def set_bio(cmd):
    cmd.need(cmd.args, "اكتب نص البايو بعد الأمر.")
    await cmd.client(functions.account.UpdateProfileRequest(about=cmd.args[:70]))
    await cmd.edit(f"✅ **تم تغيير البايو.**\n`{cmd.args[:70]}`")


@command(".يوزري", ".ضع_يوزر", section="account", usage=".يوزري <اليوزر>", desc="تغيير يوزرك")
async def set_username(cmd):
    cmd.need(cmd.args, "اكتب اليوزر الجديد بعد الأمر.")
    name = cmd.args.lstrip("@").strip()
    await cmd.client(functions.account.UpdateUsernameRequest(username=name))
    await cmd.ctx.get_me(refresh=True)
    await cmd.edit(f"✅ **تم تغيير اليوزر إلى:** @{name}")


@command(".صورتي", ".ضع_صورة", section="account", usage=".صورتي (بالرد على صورة)", desc="وضع الصورة المردود عليها كصورة حسابك")
async def set_photo(cmd):
    r = await cmd.reply_msg()
    cmd.need(r is not None and (r.photo or r.document), "رد على صورة.")
    path = await cmd.client.download_media(r)
    try:
        up = await cmd.client.upload_file(path)
        await cmd.client(functions.photos.UploadProfilePhotoRequest(file=up))
    finally:
        if path and os.path.exists(path):
            os.remove(path)
    await cmd.edit("✅ **تم تغيير صورة الحساب.**")


@command(".حذف_صورتي", ".حذف صوره", section="account", desc="حذف صورة حسابك الحالية")
async def del_photo(cmd):
    photos = await cmd.client.get_profile_photos("me", limit=1)
    cmd.need(photos, "ما عندك صورة حساب.")
    await cmd.client(functions.photos.DeletePhotosRequest(id=[photos[0]]))
    await cmd.edit("🗑 **تم حذف صورة الحساب.**")


# ───────────────────────── الخط الغامق
@command(".غامق", section="account", desc="تشغيل/إيقاف الخط الغامق لكل رسائلك العادية (يتبدل بكل مرة)")
async def bold_toggle(cmd):
    on = not cmd.ctx.state.get("bold", False)
    cmd.ctx.state.set("bold", on)
    await cmd.edit("✍️ **تم تفعيل الخط الغامق.**" if on else "✍️ **تم إيقاف الخط الغامق.**")


@listener(events.NewMessage(outgoing=True))
async def bold_apply(event, ctx):
    if not ctx.state.get("bold", False):
        return
    text = event.raw_text
    if not text or text[0] in "./" or event.message.entities or event.message.media or event.message.via_bot_id:
        return
    await event.edit(f"**{text}**")
