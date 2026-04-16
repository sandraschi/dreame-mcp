import socket
import struct
import time

def probe_vacuum(ip: str, port: int = 54321):
    # Standard MiIO "Hello" packet
    hello = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(3.0)
    
    print(f"Sending MiIO Hello to {ip}:{port}...")
    try:
        sock.sendto(hello, (ip, port))
        data, addr = sock.recvfrom(1024)
        print(f"SUCCESS: Received {len(data)} bytes from {addr}")
        print(f"RAW: {data.hex()}")
        
        # Extract metadata
        length = struct.unpack(">H", data[2:4])[0]
        did = data[12:16].hex()
        timestamp = struct.unpack(">I", data[16:20])[0]
        checksum = data[20:32].hex()
        
        print(f"Device ID: {did}")
        print(f"Timestamp: {timestamp}")
        print(f"Checksum:  {checksum}")
        
    except socket.timeout:
        print("FAILED: Timeout (no response from device)")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    probe_vacuum("192.168.0.179")
