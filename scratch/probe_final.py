import socket, sys, struct
hello = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(5)
try:
    s.sendto(hello, ("192.168.0.178", 54321))
    data, addr = s.recvfrom(1024)
    length = struct.unpack(">H", data[2:4])[0]
    did = data[12:16].hex()
    ts = struct.unpack(">I", data[16:20])[0]
    print(f"SUCCESS from {addr[0]}:{addr[1]} length={length} DID={did} ts={ts}")
    sys.exit(0)
except socket.timeout:
    print("FAIL: timeout")
    sys.exit(1)
except Exception as e:
    print(f"FAIL: {e}")
    sys.exit(1)
finally:
    s.close()
