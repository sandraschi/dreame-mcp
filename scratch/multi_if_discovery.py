import socket
import psutil
import time

def get_interfaces():
    interfaces = []
    for interface, snics in psutil.net_if_addrs().items():
        for snic in snics:
            if snic.family == socket.AF_INET:
                interfaces.append(snic.address)
    return interfaces

def discover_on_interface(interface_ip, timeout=2):
    print(f"Probing on interface: {interface_ip}...")
    # Standard MiIO Discovery Packet (32 bytes of 0xFF)
    packet = bytes.fromhex("21310020ffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        # BIND to the interface IP
        try:
            sock.bind((interface_ip, 0))
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # Send to broadcast address for the interface (assume /24 for simplicity or just 255.255.255.255)
            # We try both 255.255.255.255 and the subnet broadcast if we could calculate it.
            sock.sendto(packet, ("255.255.255.255", 54321))
            
            # Listen for responses
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    print(f"FOUND DEVICE: {addr[0]} on interface {interface_ip}")
                    print(f"Data: {data.hex()}")
                    return addr[0]
                except socket.timeout:
                    break
        except Exception as e:
            # print(f"Error on {interface_ip}: {e}")
            pass
    return None

if __name__ == "__main__":
    ips = get_interfaces()
    found_any = False
    for ip in ips:
        if ip == "127.0.0.1": continue
        res = discover_on_interface(ip)
        if res:
            found_any = True
            
    if not found_any:
        print("\nNo devices found on ANY interface.")
