"""Test miio discovery via python-miio MiIOProtocol."""
import miio.miioprotocol

proto = miio.miioprotocol.MiIOProtocol("192.168.0.178", "0"*32, 0, 0, True, 10)

try:
    info = proto.send("miIO.info", retry_count=2)
    print(f"SUCCESS: {info}", flush=True)
except Exception as e:
    print(f"FAILED: {e}", flush=True)

print("Done", flush=True)
