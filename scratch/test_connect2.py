"""Minimal connection test - step by step."""
import logging
import sys
import os
import importlib.util
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr, force=True, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from dreame_mcp.client import _stub_miio, _stub_ha, _load_module, _REF_DEFAULT, _DREAME_PKG

ref_raw = os.environ.get("DREAME_REF_PATH", "").strip()
ref_path = Path(ref_raw) if ref_raw else _REF_DEFAULT
print(f"Ref path: {ref_path}", flush=True)
print(f"Ref exists: {ref_path.exists()}", flush=True)

cc_dir = ref_path / "custom_components"
dv_dir = cc_dir / "dreame_vacuum"
dreame_dir = dv_dir / "dreame"
print(f"dreame_dir exists: {dreame_dir.exists()}", flush=True)
print(f"Files in dreame_dir: {[p.name for p in dreame_dir.iterdir()]}", flush=True)

print(f"miio installed: {importlib.util.find_spec('miio') is not None}", flush=True)

# Step 1: Stubs
_stub_miio()
_stub_ha()
import types as _types
for name, p in [
    ("custom_components", cc_dir),
    ("custom_components.dreame_vacuum", dv_dir),
    (_DREAME_PKG, dreame_dir),
]:
    m = sys.modules.get(name) or _types.ModuleType(name)
    m.__path__ = [str(p)]
    sys.modules[name] = m

print("Stubs set up", flush=True)

# Step 2: Load exceptions
try:
    _load_module(f"{_DREAME_PKG}.exceptions", dreame_dir / "exceptions.py")
    print("exceptions OK", flush=True)
except Exception as e:
    print(f"exceptions FAILED: {e}", flush=True)
    import traceback; traceback.print_exc()
    sys.exit(1)

# Step 3: Load types
try:
    _load_module(f"{_DREAME_PKG}.types", dreame_dir / "types.py")
    print("types OK", flush=True)
except Exception as e:
    print(f"types FAILED: {e}", flush=True)
    import traceback; traceback.print_exc()
    sys.exit(1)

# Step 4: Load const
try:
    _load_module(f"{_DREAME_PKG}.const", dreame_dir / "const.py")
    print("const OK", flush=True)
except Exception as e:
    print(f"const FAILED: {e}", flush=True)
    import traceback; traceback.print_exc()
    sys.exit(1)

# Step 5: Inject constants
import sys as _sys_mod
dreame_stub = _sys_mod.modules[_DREAME_PKG]
dreame_stub.DeviceException = _sys_mod.modules[f"{_DREAME_PKG}.exceptions"].DeviceException
dreame_stub.VERSION = "dreame-mcp-adapter"

print("Inject OK", flush=True)

# Step 6: Load protocol
try:
    proto_mod = _load_module(f"{_DREAME_PKG}.protocol", dreame_dir / "protocol.py")
    _protocol_cls = proto_mod.DreameVacuumProtocol
    print(f"Protocol loaded: {_protocol_cls}", flush=True)
except Exception as e:
    print(f"protocol FAILED: {e}", flush=True)
    import traceback; traceback.print_exc()
    sys.exit(1)

print("ALL GOOD - protocol loaded successfully!", flush=True)
