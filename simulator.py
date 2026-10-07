from dataclasses import dataclass, asdict
from typing import List
import math
import sys

@dataclass
class Snapshot:
    tick: int
    sender_rate: int
    receiver_window: int
    buffer_used: int
    buffer_capacity: int
    accepted: int
    dropped: int
    drained: int
    brake_level: str
    utilization: float

class FlowBrakeSimulator:
    """Receiver-driven flow-control simulation driven by the uploaded file."""

    PACKET_SIZE = 1024  # bytes represented by one transport packet

    def __init__(self):
        self.file_name = None
        self.file_size = 0
        self.total_packets = 0
        self.transferred_bytes = 0
        self.packets_sent = 0
        self.packets_received = 0
        self.reset()

    def reset(self, buffer_capacity=100, drain_rate=12, base_send_rate=25, adaptive=True):
        self.buffer_capacity = max(20, int(buffer_capacity))
        self.drain_rate = max(0, int(drain_rate))
        self.base_send_rate = max(1, int(base_send_rate))
        self.adaptive = bool(adaptive)
        self.buffer_used = 0
        self.tick = 0
        self.accepted_total = 0
        self.dropped_total = 0
        self.history: List[Snapshot] = []
        # IMPORTANT: reset does not clear the uploaded file.
        self.transferred_bytes = 0
        self.packets_sent = 0
        self.packets_received = 0

    def set_file(self, filename, size):
        self.file_name = filename
        self.file_size = max(0, int(size))
        self.total_packets = math.ceil(self.file_size / self.PACKET_SIZE) if self.file_size else 0
        self.transferred_bytes = 0
        self.packets_sent = 0
        self.packets_received = 0
        self.buffer_used = 0
        self.tick = 0
        self.accepted_total = 0
        self.dropped_total = 0
        self.history = []
        self.print_terminal_header()

    def clear_file(self):
        self.file_name = None
        self.file_size = 0
        self.total_packets = 0
        self.transferred_bytes = 0
        self.packets_sent = 0
        self.packets_received = 0
        self.history = []

    def advertised_window(self):
        free = max(0, self.buffer_capacity - self.buffer_used)
        if not self.adaptive:
            return free
        u = self.buffer_used / self.buffer_capacity
        if u >= 0.90:
            factor = 0.15
        elif u >= 0.75:
            factor = 0.35
        elif u >= 0.50:
            factor = 0.65
        else:
            factor = 1.0
        return int(free * factor)

    def brake_level(self):
        u = self.buffer_used / self.buffer_capacity
        if u >= 0.90:
            return "CRITICAL"
        if u >= 0.75:
            return "HIGH"
        if u >= 0.50:
            return "MODERATE"
        return "NORMAL"

    def step(self, incoming_rate=None, drain_rate=None, adaptive=None):
        if not self.file_size or self.transferred_bytes >= self.file_size:
            return self.state()

        if incoming_rate is None:
            incoming_rate = self.base_send_rate
        if drain_rate is None:
            drain_rate = self.drain_rate
        if adaptive is not None:
            self.adaptive = bool(adaptive)

        incoming_rate = max(0, int(incoming_rate))
        drain_rate = max(0, int(drain_rate))
        window = self.advertised_window()
        remaining_packets = self.total_packets - self.packets_sent

        # Sender is constrained by the receiver-advertised window.
        allowed = min(incoming_rate, window, remaining_packets)
        free_before = self.buffer_capacity - self.buffer_used
        accepted = min(allowed, free_before)
        dropped = max(0, incoming_rate - accepted) if remaining_packets > 0 else 0

        self.buffer_used += accepted
        self.packets_sent += accepted
        self.accepted_total += accepted
        self.dropped_total += dropped

        # Receiver consumes packets from its buffer.
        drained = min(self.buffer_used, drain_rate)
        self.buffer_used -= drained
        self.packets_received += drained

        # Only data actually received counts as transferred output.
        if drained:
            remaining_bytes = self.file_size - self.transferred_bytes
            bytes_for_packets = drained * self.PACKET_SIZE
            self.transferred_bytes += min(remaining_bytes, bytes_for_packets)

        # If all packets have arrived at the receiver, force exact completion.
        if self.packets_received >= self.total_packets:
            self.packets_received = self.total_packets
            self.transferred_bytes = self.file_size
            self.buffer_used = 0

        self.tick += 1
        snap = Snapshot(
            tick=self.tick,
            sender_rate=incoming_rate,
            receiver_window=window,
            buffer_used=self.buffer_used,
            buffer_capacity=self.buffer_capacity,
            accepted=accepted,
            dropped=dropped,
            drained=drained,
            brake_level=self.brake_level(),
            utilization=round(self.buffer_used / self.buffer_capacity * 100, 1),
        )
        self.history.append(snap)
        self.history = self.history[-60:]
        self.print_terminal_step(snap)
        return self.state()

    def print_terminal_header(self):
        """Print a clear terminal header for a new FlowBrake session."""
        print("\n" + "=" * 72, flush=True)
        print("                         FLOWBRAKE", flush=True)
        print("              Receiver-Driven Flow Control", flush=True)
        print("=" * 72, flush=True)
        print(f"File       : {self.file_name or 'No file uploaded'}", flush=True)
        if self.file_size:
            print(f"File size  : {self.file_size:,} bytes | {self.total_packets:,} packets", flush=True)
        print(f"Buffer     : {self.buffer_capacity} packets", flush=True)
        print(f"Mode       : {'ADAPTIVE' if self.adaptive else 'BASELINE'}", flush=True)
        print("-" * 72, flush=True)

    def print_terminal_step(self, snapshot):
        """Print the current simulation result in a judge-friendly format."""
        print(
            f"TICK {snapshot.tick:03d} | "
            f"Sender={snapshot.sender_rate:>3} | "
            f"Window={snapshot.receiver_window:>3} | "
            f"Accepted={snapshot.accepted:>3} | "
            f"Drained={snapshot.drained:>3} | "
            f"Limited={snapshot.dropped:>3} | "
            f"Buffer={snapshot.buffer_used:>3}/{snapshot.buffer_capacity:<3} | "
            f"Pressure={snapshot.utilization:>5.1f}% | "
            f"Brake={snapshot.brake_level}",
            flush=True,
        )

        if snapshot.brake_level == "CRITICAL":
            print("          -> Receiver is nearly full: transmission heavily restricted.", flush=True)
        elif snapshot.brake_level == "HIGH":
            print("          -> High receiver pressure: sender is strongly limited.", flush=True)
        elif snapshot.brake_level == "MODERATE":
            print("          -> Rising pressure: advertised window is reduced.", flush=True)
        else:
            print("          -> Receiver has sufficient space: normal transmission.", flush=True)

        if self.file_size:
            progress = min(100.0, self.transferred_bytes / self.file_size * 100)
            print(
                f"          File progress: {progress:5.1f}% "
                f"({self.transferred_bytes:,}/{self.file_size:,} bytes)",
                flush=True,
            )

        if self.transferred_bytes >= self.file_size and self.file_size:
            print("          *** TRANSFER COMPLETE ***", flush=True)
            print("=" * 72, flush=True)

    def state(self):
        complete = bool(self.file_size and self.transferred_bytes >= self.file_size)
        return {
            "has_file": bool(self.file_name),
            "tick": self.tick,
            "buffer_capacity": self.buffer_capacity,
            "buffer_used": self.buffer_used,
            "buffer_free": self.buffer_capacity - self.buffer_used,
            "advertised_window": self.advertised_window() if self.file_size else 0,
            "sender_rate": self.base_send_rate if self.file_size else 0,
            "drain_rate": self.drain_rate if self.file_size else 0,
            "brake_level": self.brake_level() if self.file_size else "WAITING",
            "accepted_total": self.accepted_total,
            "dropped_total": self.dropped_total,
            "adaptive": self.adaptive,
            "history": [asdict(x) for x in self.history],
            "file": {
                "name": self.file_name,
                "size": self.file_size,
                "packet_size": self.PACKET_SIZE if self.file_size else 0,
                "total_packets": self.total_packets,
                "packets_sent": self.packets_sent,
                "packets_received": self.packets_received,
                "transferred": self.transferred_bytes,
                "remaining": max(0, self.file_size - self.transferred_bytes),
                "progress": round(self.transferred_bytes / self.file_size * 100, 1) if self.file_size else 0,
                "complete": complete,
            },
        }


def run_terminal_demo():
    """Run a small standalone demonstration for judges from the terminal."""
    sim = FlowBrakeSimulator()
    sim.reset(buffer_capacity=100, drain_rate=10, base_send_rate=20, adaptive=True)
    sim.set_file("terminal_demo.dat", 250 * sim.PACKET_SIZE)

    print("\nDEMO: BASELINE -> PRESSURE -> RECOVERY", flush=True)
    print("This is a terminal-only demonstration of receiver-driven flow control.\n", flush=True)

    # 1. Baseline: sender is slower than the receiver, so pressure stays low.
    print("\n[1] BASELINE — receiver has enough capacity", flush=True)
    print("Sender sends slowly; receiver keeps up.\n", flush=True)
    for _ in range(4):
        sim.step(incoming_rate=12, drain_rate=10, adaptive=True)

    # 2. Pressure: sender becomes much faster than the receiver.
    print("\n[2] PRESSURE — sender is faster than receiver", flush=True)
    print("Buffer fills, pressure rises, and the advertised window limits the sender.\n", flush=True)
    for _ in range(12):
        sim.step(incoming_rate=80, drain_rate=5, adaptive=True)

    # 3. Recovery: receiver drains faster than the sender sends.
    print("\n[3] RECOVERY — receiver catches up", flush=True)
    print("Buffer drains and pressure falls, allowing transmission to recover.\n", flush=True)
    for _ in range(10):
        sim.step(incoming_rate=20, drain_rate=30, adaptive=True)

    print("\n" + "=" * 72, flush=True)
    print("                         DEMO COMPLETE", flush=True)
    print("=" * 72, flush=True)
    print(
        f"Final buffer: {sim.buffer_used}/{sim.buffer_capacity} packets | "
        f"Pressure: {sim.buffer_used / sim.buffer_capacity * 100:.1f}% | "
        f"Brake: {sim.brake_level()}",
        flush=True,
    )
    print("\nStart the web interface with: python app.py", flush=True)


if __name__ == "__main__":
    run_terminal_demo()
