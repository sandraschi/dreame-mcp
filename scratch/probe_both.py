import socket
import struct

def probe(ip):
    hello = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    try:
        sock.sendto(hello, (ip, 54321))
        data, addr = sock.recvfrom(1024)
        did = data[12:16].hex()
        print(f"{ip}: SUCCESS - DeviceID={did}")
    except socket.timeout:
        print(f"{ip}: Timeout")
    except Exception as e:
        print(f"{ip}: Error: {e}")
    finally:
        sock.close()

probe("192.168.0.178")
probe("192.168.0.179")
