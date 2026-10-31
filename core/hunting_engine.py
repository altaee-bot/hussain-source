"""
محرك الصيد والتثبيت — يعمل بالخلفية لكل حساب بشكل مستقل.

إصلاح مهم عن النسخة القديمة: كانت أي خطأ (حتى انقطاع الانترنت أو FloodWait) يُعتبر
"اليوزر متاح" فتبدأ تنشئ قنوات بلا فائدة. الآن فقط UsernameNotOccupied = متاح.
"""
import asyncio
import random
import re
import string

from telethon import errors, functions

LETTERS = string.ascii_lowercase
DIGITS = string.digits
USER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")

MODES = {"triple": 3, "quad": 4, "penta": 5}
MODE_NAMES = {"triple": "ثلاثيات", "quad": "رباعيات", "penta": "خماسيات"}


def valid_username(name):
    return bool(USER_RE.match(name)) and "__" not in name and not name.endswith("_")


def random_username(mode):
    """يولّد يوزر بفواصل: a_1_z — أول خانة حرف دائماً (شرط تيليجرام)."""
    n = MODES[mode]
    chars = LETTERS + DIGITS
    parts = [random.choice(LETTERS)] + [random.choice(chars) for _ in range(n - 1)]
    return "_".join(parts)


async def is_available(client, username):
    """True متاح، False مأخوذ، None تعذر الفحص (فلود/شبكة)."""
    if not valid_username(username):
        return False
    try:
        await client(functions.contacts.ResolveUsernameRequest(username=username))
        return False
    except errors.UsernameNotOccupiedError:
        return True
    except errors.UsernameInvalidError:
        return False
    except errors.FloodWaitError as e:
        await asyncio.sleep(min(e.seconds + 1, 600))
        return None
    except Exception:
        return None


async def hunting_engine(client, ctx, mode, target_user=None, event=None):
    attempts = 0
    task_key = target_user or mode
    channel_id = None
    errors_in_row = 0
    while task_key in ctx.hunting_tasks:
        attempts += 1
        try:
            current = target_user or random_username(mode)
            avail = await is_available(client, current)
            if avail is None:
                errors_in_row += 1
                if errors_in_row >= 15:
                    await client.send_message("me", f"⚠️ توقف الصيد `{task_key}` بسبب أخطاء اتصال متكررة.")
                    ctx.hunting_tasks.pop(task_key, None)
                    return
                await asyncio.sleep(3)
                continue
            errors_in_row = 0
            if not avail:
                await asyncio.sleep(1.0 if target_user else 0.35)
                continue

            # متاح: ننشئ قناة (مرة وحدة للمهمة) ونثبّت اليوزر عليها
            if not channel_id:
                created = await client(functions.channels.CreateChannelRequest(
                    title=f"Reco Hunt: @{current}", about="تم الصيد بواسطة سورس ريكو المطور", megagroup=False))
                channel_id = created.chats[0].id
            try:
                await client(functions.channels.UpdateUsernameRequest(channel=channel_id, username=current))
            except (errors.UsernameOccupiedError, errors.UsernameInvalidError):
                await asyncio.sleep(0.5)
                continue
            msg = (f"✨ **تم الاقتناص بنجاح!** ✨\n‏┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉┉\n💎 **اليوزر:** @{current}\n"
                   f"🔢 **المحاولات:** `{attempts}`\n📡 **النوع:** "
                   f"{'تثبيت محدد' if target_user else MODE_NAMES.get(mode, mode)}\n🔗 t.me/{current}")
            await client.send_message("me", msg)
            if event is not None:
                try:
                    await event.respond(msg)
                except Exception:
                    pass
            if target_user:
                ctx.hunting_tasks.pop(task_key, None)
                return
            channel_id = None
        except asyncio.CancelledError:
            raise
        except errors.FloodWaitError as e:
            await asyncio.sleep(min(e.seconds + 1, 900))
        except Exception as e:
            if "CHANNELS_ADMIN_PUBLIC_TOO_MUCH" in str(e):
                await client.send_message("me", "⚠️ حسابك ممتلئ بالقنوات العامة، احذف قناة عامة ثم أعد الصيد.")
                ctx.hunting_tasks.pop(task_key, None)
                return
            await asyncio.sleep(2)
