"""Discover Dreame/Xiaomi miio devices on the LAN.

Two passes:
  1. UDP hello broadcast sweep on port 54321 (the miio discovery handshake)
  2. mDNS scan for the _miio._udp service

Usage: uv run python scripts/discover.py [--timeout 15]
Exit 0 when at least one miio device answers, 1 otherwise.
"""

import argparse
import socket
import struct
import sys
import time

MIIO_PORT = 54321
HELLO_MAGIC = b"\x21\x31\x00\x20"


def make_hello() -> bytes:
    return struct.pack(">4sI", HELLO_MAGIC, int(time.time())) + b"\x00" * 8


def udp_hello_probe(ip: str, timeout: float = 0.7) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    try:
        s.sendto(make_hello(), (ip, MIIO_PORT))
        data, _ = s.recvfrom(128)
        return bool(data) and data[:2] == HELLO_MAGIC[:2]
    except (TimeoutError, OSError):
        return False
    finally:
        s.close()


def ping_alive(ip: str) -> bool:
    import subprocess

    r = subprocess.run(
        ["ping", "-n", "1", "-w", "150", ip],
        capture_output=True,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )
    return r.returncode == 0


def sweep(network: str = "192.168.0", timeout: float = 0.7) -> list[str]:
    alive = [f"{network}.{i}" for i in range(1, 255) if ping_alive(f"{network}.{i}")]
    found = [ip for ip in alive if udp_hello_probe(ip, timeout)]
    return found


def mdns_scan() -> list[str]:
    try:
        from miio.discovery import Discovery

        found = Discovery.discover_mdns()
        if not found:
            return []
        if isinstance(found, dict):
            return list(found.keys())
        return [getattr(d, "ip", str(d)) for d in found]
    except Exception as e:
        print(f"  [mdns] scan failed: {e}", file=sys.stderr)
        return []


def main() -> int:
    p = argparse.ArgumentParser(description="Discover Dreame/Xiaomi miio devices on the LAN")
    p.add_argument("--timeout", type=float, default=0.7, help="UDP probe timeout per host")
    p.add_argument("--network", default="192.168.0", help="IPv4 /24 to sweep (default 192.168.0)")
    args = p.parse_args()

    print(f"Sweeping {args.network}.1-254 for miio devices (UDP {MIIO_PORT})...", flush=True)
    found = sweep(args.network, args.timeout)
    if not found:
        print("No miio device answered UDP discovery on this subnet.", flush=True)
        print("Checking mDNS (_miio._udp)...", flush=True)
        found = mdns_scan()

    if not found:
        print(
            "\nNo Dreame/Xiaomi device found on the LAN.\n"
            "Check: robot powered on and docked, Wi-Fi connected, same network as this PC.\n"
            "If the robot's IP changed, add the new IP to DREAME_IP in .env.",
            file=sys.stderr,
        )
        return 1

    print("\nFound miio device(s):")
    for ip in found:
        print(f"  - {ip}  (set DREAME_IP={ip} in .env)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
