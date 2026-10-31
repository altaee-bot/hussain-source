"""طلبات HTTP غير حاجبة (aiohttp) — بديل requests داخل الأوامر كي ما يتجمّد السورس."""
import asyncio
import json as _json

import aiohttp

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) RecoSource/16"}
_session = None


def session():
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers=_UA, timeout=aiohttp.ClientTimeout(total=20))
    return _session


async def get_json(url, params=None, timeout=15, headers=None):
    async with session().get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
        r.raise_for_status()
        txt = await r.text()
        return _json.loads(txt)


async def get_text(url, params=None, timeout=15, headers=None):
    async with session().get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
        r.raise_for_status()
        return await r.text()


async def post_json(url, payload, timeout=20, headers=None, params=None):
    async with session().post(url, json=payload, params=params, headers=headers,
                              timeout=aiohttp.ClientTimeout(total=timeout)) as r:
        r.raise_for_status()
        return await r.json(content_type=None)


async def get_bytes(url, timeout=20, max_bytes=15 * 1024 * 1024):
    async with session().get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
        r.raise_for_status()
        data = await r.content.read(max_bytes)
        return data


async def to_thread(fn, *a, **kw):
    """تشغيل دالة حاجبة بخيط منفصل."""
    return await asyncio.to_thread(fn, *a, **kw)
