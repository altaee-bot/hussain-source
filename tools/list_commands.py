"""يطبع كل أوامر السورس مرتبة بالأقسام:  python tools/list_commands.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import catalog, loader  # noqa: E402

loader.import_plugins(verbose=False)
total = 0
for num, key, icon, title in catalog.SECTIONS:
    specs = catalog.commands_of(key)
    total += len(specs)
    print(f"\n{icon} م{num} — {title} ({len(specs)})")
    for s in specs:
        print(f"   {s.names[0]:<22} {s.desc}")
print(f"\nالمجموع: {total} أمر ظاهر")
