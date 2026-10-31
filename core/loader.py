"""
محمّل الأوامر: يستورد كل ملفات plugins/ مرة وحدة (الأوامر تتسجل بـ @command).
أي ملف فيه خطأ يُتخطى ويُطبع سببه، وباقي الأوامر تشتغل.
لإضافة أمر جديد: اعمل ملف .py داخل plugins/<قسم>/ واستعمل @command — وخلاص.
"""
import importlib
import logging
import pkgutil
import traceback

import plugins

log = logging.getLogger("reco")
_LOADED = {"ok": [], "failed": []}


def iter_plugin_names():
    for mod in pkgutil.walk_packages(plugins.__path__, prefix="plugins."):
        leaf = mod.name.rsplit(".", 1)[-1]
        if mod.ispkg or leaf.startswith("_"):
            continue
        yield mod.name


def import_plugins(verbose=True):
    """يستورد كل الإضافات (مرة وحدة لكل العملية)."""
    if _LOADED["ok"] or _LOADED["failed"]:
        return _LOADED["ok"], _LOADED["failed"]
    for name in sorted(iter_plugin_names()):
        try:
            importlib.import_module(name)
            _LOADED["ok"].append(name)
        except Exception as e:
            _LOADED["failed"].append((name, e))
            if verbose:
                print(f"❌ فشل تحميل {name}: {e}")
                traceback.print_exc()
    return _LOADED["ok"], _LOADED["failed"]


def load_plugins(client, ctx, verbose=True):
    """يربط الأوامر بحساب. (يستورد الملفات أول مرة فقط)."""
    from core import framework
    ok, failed = import_plugins(verbose)
    framework.attach(client, ctx)
    if verbose:
        print(f"✅ ريكو: {len(framework.REGISTRY)} أمر + {len(framework.LISTENERS)} مستمع من {len(ok)} ملف"
              + (f" | ❌ فشل {len(failed)} ملف" if failed else ""))
    return ok, failed
