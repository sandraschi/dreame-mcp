import socket
import time

def probe_vacuum(ip, port=54321):
    # Standard miIO discovery packet (32 bytes)
    # 21 31 00 20 ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff
    packet = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    
    print(f"--- Probing {ip}:{port} ---")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    
    try:
        start_time = time.time()
        sock.sendto(packet, (ip, port))
        data, addr = sock.recvfrom(1024)
        elapsed = time.time() - start_time
        print(f"Response from {addr} in {elapsed:.3f}s: {data.hex()}")
        return True
    except socket.timeout:
        print("Timeout: No response from robot.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        sock.close()

if __name__ == "__main__":
    probe_vacuum("192.168.0.179")
