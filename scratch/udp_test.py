import socket, struct

def probe(ip, port=54321, label=""):
    hello = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    try:
        sock.sendto(hello, (ip, port))
        data, addr = sock.recvfrom(1024)
        did = data[12:16].hex()
        print(f"{label or ip}: SUCCESS - DeviceID={did}")
    except socket.timeout:
        print(f"{label or ip}: Timeout on port {port}")
    except Exception as e:
        print(f"{label or ip}: Error: {e}")
    finally:
        sock.close()

# Also try the common alternate ports
for p in [54321, 32123]:
    probe("192.168.0.178", p, f"178 port {p}")
probe("192.168.0.179", 54321, "179 port 54321")
