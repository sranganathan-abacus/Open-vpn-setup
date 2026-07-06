#!/usr/bin/env python3

import struct
import sys
import argparse
from enum import Enum

class Flow(Enum):
    CONTROL    = "CONTROL"     # ICMP / ICMPv6
    MANAGEMENT = "MANAGEMENT"  # TCP port 443 / 80
    DATA       = "DATA"        # everything else
    UNKNOWN    = "UNKNOWN"     # non-IP or truncated

def classify_packet(raw: bytes) -> Flow:
    if len(raw) < 1:
        return Flow.UNKNOWN

    version = (raw[0] >> 4) & 0x0F

    # ── IPv4 ──
    if version == 4:
        if len(raw) < 20:
            return Flow.UNKNOWN
        ihl   = (raw[0] & 0x0F) * 4
        proto = raw[9]

        dst_port = 0
        if proto in (6, 17) and len(raw) >= ihl + 4:   # TCP or UDP
            dst_port = struct.unpack("!H", raw[ihl+2:ihl+4])[0]

        if proto == 1:                          # ICMP
            return Flow.CONTROL
        if proto == 6 and dst_port in (443, 80):  # HTTPS / HTTP
            return Flow.MANAGEMENT
        return Flow.DATA

    # ── IPv6 ──
    if version == 6:
        if len(raw) < 40:
            return Flow.UNKNOWN
        next_hdr = raw[6]
        if next_hdr == 58:                      # ICMPv6
            return Flow.CONTROL
        return Flow.DATA

    return Flow.UNKNOWN

def handle_control(raw: bytes, meta: str):
    print(f"  [CONTROL]    {meta}  len={len(raw)}  → forward as-is / log latency")

def handle_management(raw: bytes, meta: str):
    print(f"  [MANAGEMENT] {meta}  len={len(raw)}  → priority queue / mirror")

def handle_data(raw: bytes, meta: str):
    print(f"  [DATA]       {meta}  len={len(raw)}  → normal bulk forward")

def handle_unknown(raw: bytes, meta: str):
    print(f"  [UNKNOWN]    {meta}  len={len(raw)}  → drop / log")

DISPATCH = {
    Flow.CONTROL:    handle_control,
    Flow.MANAGEMENT: handle_management,
    Flow.DATA:       handle_data,
    Flow.UNKNOWN:    handle_unknown,
}

def segregate_packet(raw: bytes, meta: str = ""):
    flow = classify_packet(raw)
    DISPATCH[flow](raw, meta)
    return flow

def build_ipv4(proto: int, src="10.8.0.1", dst="10.8.0.2",
               sport: int = 1234, dport: int = 0, payload: bytes = b"\x00" * 20) -> bytes:
    """Build a minimal IPv4 packet (no checksum needed for classification)."""
    src_b = bytes(int(x) for x in src.split("."))
    dst_b = bytes(int(x) for x in dst.split("."))
    total_len = 20 + len(payload)
    if proto in (6, 17):  # TCP/UDP: prepend src/dst ports
        payload = struct.pack("!HH", sport, dport) + payload

    hdr = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,        # version=4, IHL=5
        0,           # DSCP/ECN
        total_len + (4 if proto in (6,17) else 0),
        0,           # ID
        0,           # flags/frag
        64,          # TTL
        proto,
        0,           # checksum (skip)
        src_b,
        dst_b,
    )
    return hdr + payload

def build_icmp() -> bytes:
    return build_ipv4(proto=1, payload=b"\x08\x00\x00\x00\x00\x01\x00\x01" + b"\xab"*56)

def build_tcp(dport: int) -> bytes:
    return build_ipv4(proto=6, dport=dport, payload=b"\x00"*20)

def build_udp(dport: int) -> bytes:
    return build_ipv4(proto=17, dport=dport, payload=b"\x00"*10)

def build_ipv6_icmpv6() -> bytes:
    # version=6, TC=0, FL=0, payload_len=8, next=58 (ICMPv6), hop=64
    hdr = struct.pack("!IHBB", 0x60000000, 8, 58, 64)
    src = bytes(16)   # ::
    dst = bytes(16)   # ::
    return hdr + src + dst + b"\x80\x00\x00\x00\x00\x00\x00\x00"

TESTS = [
    ("ICMP echo (ping)",          build_icmp(),              Flow.CONTROL),
    ("TCP → port 443 (HTTPS)",    build_tcp(443),            Flow.MANAGEMENT),
    ("TCP → port 80 (HTTP)",      build_tcp(80),             Flow.MANAGEMENT),
    ("TCP → port 22 (SSH)",       build_tcp(22),             Flow.DATA),
    ("UDP → port 1194 (OpenVPN)", build_udp(1194),           Flow.DATA),
    ("UDP → port 53 (DNS)",       build_udp(53),             Flow.DATA),
    ("IPv6 ICMPv6",               build_ipv6_icmpv6(),       Flow.CONTROL),
    ("Truncated / garbage",       b"\xff\x00",               Flow.UNKNOWN),
    ("Empty buffer",              b"",                       Flow.UNKNOWN),
]

def run_tests():
    print("=" * 60)
    print("  Packet Segregator – built-in test suite")
    print("=" * 60)
    passed = failed = 0
    for name, raw, expected in TESTS:
        flow = segregate_packet(raw, name)
        ok   = flow == expected
        status = "PASS" if ok else f"FAIL (expected {expected.value})"
        print(f"  {'✓' if ok else '✗'}  {name:35s}  {status}")
        if ok: passed += 1
        else:  failed += 1
    print("-" * 60)
    print(f"  {passed} passed  {failed} failed")
    print("=" * 60)
    return failed == 0

def run_live(iface: str = "tun0"):
    try:
        from scapy.all import sniff, raw as scapy_raw
    except ImportError:
        print("scapy not found.  Install with:  pip install scapy")
        sys.exit(1)

    print(f"[live] sniffing on {iface}  (Ctrl-C to stop)")

    def handle(pkt):
        raw = bytes(pkt)
        meta = f"src={pkt.src if hasattr(pkt,'src') else '?'}"
        segregate_packet(raw, meta)

    sniff(iface=iface, prn=handle, store=False)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Packet segregator demo")
    ap.add_argument("--live",  action="store_true", help="sniff live packets from tun0")
    ap.add_argument("--iface", default="tun0",      help="interface for --live mode")
    args = ap.parse_args()

    if args.live:
        run_live(args.iface)
    else:
        ok = run_tests()
        sys.exit(0 if ok else 1)
