import socket
import concurrent.futures
import time

def check_ip(ip, port=54321, timeout=0.1):
    # Standard miIO discovery packet (32 bytes)
    packet = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.sendto(packet, (ip, port))
            data, addr = sock.recvfrom(1024)
            return addr[0], data.hex()
        except Exception:
            return None

def scan_subnet(subnet_prefix):
    print(f"Scanning {subnet_prefix}.x...")
    ips = [f"{subnet_prefix}.{i}" for i in range(1, 255)]
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        future_to_ip = {executor.submit(check_ip, ip): ip for ip in ips}
        for future in concurrent.futures.as_completed(future_to_ip):
            res = future.result()
            if res:
                results.append(res)
                print(f"FOUND device at {res[0]}!")
    return results

if __name__ == "__main__":
    found = []
    found.extend(scan_subnet("192.168.0"))
    found.extend(scan_subnet("192.168.1"))
    
    if found:
        print("\n--- Summary of Found Devices ---")
        for ip, data in found:
            print(f"IP: {ip} | Packet: {data}")
    else:
        print("\nNo devices found in either subnet.")
