"""Test Xiaomi MiHome cloud protocol."""
import logging, sys, os, importlib
from pathlib import Path

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv
load_dotenv()

# Bootstrap loads packages into sys.modules
import dreame_mcp.client as mc

ref_path = Path(os.environ.get("DREAME_REF_PATH", "D:/Dev/repos/tasshack_dreame_vacuum_ref"))
mc._bootstrap_protocol(ref_path)

# Now the protocol module is loaded in sys.modules
proto_mod = sys.modules["custom_components.dreame_vacuum.dreame.protocol"]
MiHomeCls = getattr(proto_mod, "DreameVacuumMiHomeCloudProtocol", None)
print(f"MiHomeCloudProtocol: {MiHomeCls}", flush=True)

username = os.environ.get("DREAME_USER", "").strip()
password = os.environ.get("DREAME_PASSWORD", "").strip()
country = os.environ.get("DREAME_COUNTRY", "eu").strip()
did = os.environ.get("DREAME_DID", "2045852486").strip()

if MiHomeCls:
    proto = MiHomeCls(
        username=username,
        password=password,
        country=country,
        auth_key=None,
        device_id=did,
    )
    ok = proto.login()
    print(f"MiHome login: {ok}", flush=True)
    if ok:
        devices = proto.get_devices()
        print(f"Devices: {devices}", flush=True)
    else:
        print(f"Login failed. auth_failed: {proto.auth_failed}", flush=True)
else:
    print("MiHomeCloudProtocol not available", flush=True)
