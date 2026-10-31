"""
محركات الذكاء الاصطناعي لأمر .ذكاء — تُجرَّب كلها بالتوازي ويُؤخذ أسرع جواب صالح
(قبل كانت تتجرب وحدة وحدة بانتظار 5 ثواني لكل محرك = دقيقة ضايعة).

لأفضل جودة: ضع مفتاح Gemini المجاني بمتغير البيئة GEMINI_API_KEY (من aistudio.google.com).
وتقدر تضيف محركاتك: RECO_AI_URLS="https://site/api?q={q}|https://site2/api?text={q}"
"""
import asyncio
import os
from urllib.parse import quote

from core import netutil

DEFAULT_URLS = [
    "https://hercai.onrender.com/v3/hercai?question={q}",
    "https://api.popcat.xyz/chatbot?msg={q}&owner=Reco&botname=Reco",
    "https://darkness.ashlynn.workers.dev/chat?q={q}",
    "https://api.vyturex.com/chatgpt?prompt={q}",
    "https://sandipbaruwal.onrender.com/gpt?prompt={q}",
    "https://aivurex.onrender.com/gpt?prompt={q}",
]
KEYS = ("answer", "gpt", "response", "reply", "out", "message", "result", "text", "content")


def _extract(data):
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for k in KEYS:
            v = data.get(k)
            if isinstance(v, str) and len(v.strip()) > 2:
                return v
            if isinstance(v, (dict, list)):
                r = _extract(v)
                if r:
                    return r
    if isinstance(data, list):
        for item in data:
            r = _extract(item)
            if r:
                return r
    return None


async def _gemini(prompt):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    data = await netutil.post_json(url, {"contents": [{"parts": [{"text": prompt}]}]}, params={"key": key}, timeout=25)
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def _url_engine(template, prompt):
    data = await netutil.get_json(template.replace("{q}", quote(prompt)), timeout=12)
    return _extract(data)


async def get_super_ai_response(prompt):
    custom = [u.strip() for u in os.getenv("RECO_AI_URLS", "").split("|") if "{q}" in u]
    tasks = [asyncio.create_task(_gemini(prompt))]
    tasks += [asyncio.create_task(_url_engine(u, prompt)) for u in custom + DEFAULT_URLS]
    try:
        for fut in asyncio.as_completed(tasks, timeout=30):
            try:
                ans = await fut
            except Exception:
                continue
            if ans and len(str(ans).strip()) > 2:
                return str(ans).strip()
    except asyncio.TimeoutError:
        pass
    finally:
        for t in tasks:
            t.cancel()
    return None
