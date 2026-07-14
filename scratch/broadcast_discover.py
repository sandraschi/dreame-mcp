"""Try broadcast and interface-specific miio discovery."""
import socket, sys

hello = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")

# Try via specific interface IP
ips = {"192.168.0.81": "Ethernet", "192.168.1.87": "WiFi"}
for bind_ip, label in ips.items():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(3)
        s.bind((bind_ip, 0))
        s.sendto(hello, ("192.168.0.178", 54321))
        data, addr = s.recvfrom(1024)
        did = data[12:16].hex()
        print(f"[{label} {bind_ip}] Unicast success from {addr[0]}: DID={did}", flush=True)
        s.close()
        continue
    except socket.timeout:
        print(f"[{label} {bind_ip}] Unicast timeout", flush=True)
    except Exception as e:
        print(f"[{label} {bind_ip}] Error: {e}", flush=True)
    s.close()

# Try broadcast on Ethernet
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.settimeout(5)
try:
    s.bind(("192.168.0.81", 0))
    s.sendto(hello, ("192.168.0.255", 54321))
    print("Broadcast on 192.168.0.255 sent...", flush=True)
    data, addr = s.recvfrom(1024)
    did = data[12:16].hex()
    print(f"Broadcast response from {addr[0]}: DID={did}", flush=True)
except socket.timeout:
    print("No broadcast response", flush=True)
except Exception as e:
    print(f"Broadcast error: {e}", flush=True)
finally:
    s.close()
