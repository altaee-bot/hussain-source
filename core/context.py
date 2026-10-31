"""
Ctx = حالة حساب واحد.

السورس يشغّل عدة حسابات داخل نفس العملية، لذلك أي متغير خاص بالحساب
(المساعدين، المكتومين، مهام الصيد ...) لازم يكون هنا — وليس متغير عام بملف.
القيم الدائمة تنحفظ بـ ctx.state (تبقى بعد إعادة التشغيل)،
والمؤقتة (مهام شغالة) تبقى بالذاكرة فقط.
"""
import os
import time
from datetime import datetime

from core.constants import DATA_ROOT
from core.state import State
from core.storage import load_json, save_json


class Ctx:
    def __init__(self, client, install_info=None):
        self.client = client
        self.install_info = install_info or {}
        self.start_time = datetime.now()
        self._me = None
        self.data_dir = os.path.join(DATA_ROOT, "_unknown")
        self.state = State()

        # ── مؤقت (لا يُحفظ)
        self.msg_cache = {}
        self.storage_pv = None
        self.storage_groups = None
        self.storage_deleted = None
        self.time_task = None
        self.original_profile = {}
        self.reply_state = {}
        self.hunting_tasks = {}
        self.auto_tasks = {}
        self.add_group_data = {}
        self.group_publish = {"links": [], "message": "", "delay": 300, "count": 0,
                              "sent": {}, "tasks": {}, "last_sent": {}}
        self.responses = {}
        self.cache = {}            # كاش عام قصير العمر
        self._cooldowns = {}

    # ── قيم دائمة (قوائم تنحفظ تلقائياً)
    @property
    def helpers(self):
        return self.state.list("helpers")

    @property
    def muted_users(self):
        return self.state.list("muted")

    def save(self):
        self.state.save_soon()

    # ── الحساب
    async def get_me(self, refresh=False):
        if self._me is None or refresh:
            self._me = await self.client.get_me()
        return self._me

    async def load_state(self):
        me = await self.get_me()
        self.data_dir = os.path.join(DATA_ROOT, str(me.id))
        os.makedirs(self.data_dir, exist_ok=True)
        self.state.load(os.path.join(self.data_dir, "state.json"))
        self.responses = self._migrate_responses(load_json(os.path.join(self.data_dir, "responses.json"), {}))

    @staticmethod
    def _migrate_responses(raw):
        """الصيغة القديمة {كلمة: جواب} ← الجديدة {مفتاح: {word, answer}}."""
        out = {}
        for k, v in (raw or {}).items():
            if isinstance(v, dict):
                out[k] = v
            else:
                out[" ".join(str(k).split()).casefold()] = {"word": str(k), "answer": str(v)}
        return out

    def save_responses(self):
        save_json(os.path.join(self.data_dir, "responses.json"), self.responses)

    # ── أدوات صغيرة
    def cooldown(self, key, seconds):
        """True لو مسموح (ويبدأ العد)، False لو لسه ضمن فترة الانتظار."""
        now = time.monotonic()
        if now - self._cooldowns.get(key, 0) < seconds:
            return False
        self._cooldowns[key] = now
        if len(self._cooldowns) > 2000:
            self._cooldowns = {k: v for k, v in self._cooldowns.items() if now - v < 3600}
        return True

    def cached(self, key, ttl):
        item = self.cache.get(key)
        if item and time.monotonic() - item[0] < ttl:
            return item[1]
        return None

    def put_cache(self, key, value):
        self.cache[key] = (time.monotonic(), value)
        return value
