"""حفظ حالة كل حساب بملف JSON (مساعدين، مكتومين، إعدادات...) — كي لا تضيع بعد إعادة التشغيل."""
import json
import os
import threading


class State:
    def __init__(self, path=None):
        self.path = path
        self.data = {}
        self._timer = None
        self._lock = threading.Lock()

    def load(self, path):
        self.path = path
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                # ندمج ما كان في الذاكرة قبل التحميل مع الملف
                loaded.update({k: v for k, v in self.data.items() if k not in loaded})
                self.data = loaded
        except FileNotFoundError:
            pass
        except Exception as e:  # ملف تالف: نحتفظ بنسخة ونبدأ نظيف
            try:
                os.replace(path, path + ".bak")
            except OSError:
                pass
            print(f"⚠️ ملف الحالة تالف ({e}) — تم عمل نسخة .bak")

    # ── قراءة/كتابة
    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save_soon()

    def list(self, key):
        v = self.data.get(key)
        if not isinstance(v, list):
            v = self.data[key] = []
        return v

    def dict(self, key):
        v = self.data.get(key)
        if not isinstance(v, dict):
            v = self.data[key] = {}
        return v

    # ── حفظ مؤجّل (يجمع عدة تعديلات بحفظة واحدة)
    def save_soon(self, delay=1.0):
        if not self.path:
            return
        with self._lock:
            if self._timer is not None:
                return
            t = threading.Timer(delay, self._flush_timer)
            t.daemon = True
            self._timer = t
            t.start()

    def _flush_timer(self):
        with self._lock:
            self._timer = None
        self.save()

    def save(self):
        if not self.path:
            return
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception as e:
            print(f"⚠️ تعذر حفظ الحالة: {e}")
