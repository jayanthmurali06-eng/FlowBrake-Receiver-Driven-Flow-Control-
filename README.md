# FlowBrake — Receiver-Driven Flow Control

## 1. Project idea

FlowBrake VisualLab follows a local-first experiment-lab approach: the browser provides control and observability while the simulation engine models receiver-driven flow control.

**FlowBrake** is an educational Computer Networks mini-project that demonstrates receiver-driven flow control.

The receiver monitors its available buffer and advertises a window to the sender. The sender is expected to respect that window. FlowBrake adds an adaptive demonstration layer: as receiver-buffer utilization rises, the advertised allowance is reduced more aggressively.

This is a **simulation**, not a replacement for TCP and does not send real network packets.

## 2. Problem statement

A sender may generate data faster than a receiver can process it. If the receiver's buffer fills, excess data can be rejected or create inefficient behavior. A receiver-driven mechanism gives the receiver a way to communicate its current capacity to the sender.

## 3. Objectives

- Simulate sender → receiver data flow.
- Model receiver buffer occupancy.
- Calculate an advertised receive window.
- Make sender transmission obey the receiver window.
- Demonstrate adaptive braking as the buffer fills.
- Visualize buffer usage and window changes.
- Compare adaptive and non-adaptive behavior.

## 4. Architecture

Sender → Data → Receiver Buffer → Application Drain
             ↑
        Advertised Window
             ↑
          FlowBrake

## 5. Algorithm

At every simulation tick:

1. Measure receiver buffer usage.
2. Compute free buffer = capacity − used.
3. If adaptive mode is disabled, advertised window = free buffer.
4. If adaptive mode is enabled:
   - utilization < 50% → 100% of free space
   - 50–75% → 65% of free space
   - 75–90% → 35% of free space
   - >90% → 15% of free space
5. Sender transmits at most the advertised window.
6. Receiver accepts the allowed data.
7. Receiver drains data at its processing rate.
8. Repeat and visualize.

## 6. Why this is receiver-driven

The important direction is the control signal:

**Receiver → Sender: "This is how much data I can currently accept."**

The sender does not decide the receiver's capacity. It reacts to the receiver's advertised window.

## 7. Research gap / project novelty

TCP already provides receiver flow control through the advertised receive window. RFC 9293 describes RCV.WND as the amount of data the receiver is currently prepared to accept. citeturn0search1

The mini-project therefore should NOT claim to invent receiver-driven flow control. Its contribution is an educational adaptive control model that makes the receiver's buffer state visible and demonstrates how progressively tighter receiver feedback changes sender behavior.

A useful extension for future work is to compare:
- static receive-window flow control,
- adaptive receiver braking,
- congestion-controlled TCP behavior,
- different buffer sizes and drain rates,
- packet-level simulation using ns-3.

## 8. Running the project

### macOS / Linux

```bash
cd FlowBrake
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open:

http://127.0.0.1:5000

### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

## 9. Demo scenarios

### Scenario A — Healthy receiver
Sender: 20
Drain: 20
Buffer: 100
Expected: buffer stays low and brake remains NORMAL.

### Scenario B — Receiver under pressure
Sender: 60
Drain: 10
Buffer: 100
Expected: buffer rises, advertised window falls, brake changes to MODERATE/HIGH/CRITICAL.

### Scenario C — Recovery
While the buffer is high, increase drain rate to 40.
Expected: buffer falls and the advertised window increases again.

### Scenario D — Disable adaptive brake
Turn off Adaptive brake.
Expected: advertised window becomes the raw free buffer space. This gives a useful comparison against the proposed adaptive layer.

## 10. Limitations

- It is not a real TCP implementation.
- It uses abstract "units" instead of bytes/segments.
- It does not model packet loss, RTT, retransmission, congestion window, or real sockets.
- The adaptive thresholds are project-design parameters, not TCP standards.

## 11. Future scope

- Add real TCP socket experiments.
- Add packet-loss and RTT simulation.
- Compare FlowBrake against a baseline using statistical metrics.
- Add ns-3 implementation.
- Tune adaptive thresholds automatically.
- Evaluate throughput, buffer overflow, delay, and fairness.

## 12. References

1. RFC 9293 — Transmission Control Protocol (TCP), IETF/RFC Editor.
2. RFC 5681 — TCP Congestion Control, IETF/RFC Editor.
3. RFC 9840 — rLEDBAT: Receiver-Driven Low Extra Delay Background Transport for TCP, IETF/RFC Editor.

## 13. File upload demo

The web UI now includes a **Sender → Receiver file-transfer panel**.

1. Click **Choose File** or drag a file into the upload box.
2. Click **Upload & Start Transfer**.
3. Flask stores the uploaded file locally in `uploads/`.
4. The FlowBrake simulator visualizes the file moving through the receiver-controlled transmission window.
5. When the simulated transfer reaches 100%, **Download Received File** becomes available.

Supported data is not restricted to one format. The browser can upload text files, images, PDFs, audio, video, ZIP files, and other file types. The demo accepts files up to 500 MB.

**Important:** the transfer visualization uses simulation units rather than real network packets/bytes. The actual uploaded file is stored locally; FlowBrake demonstrates how receiver feedback limits the sender's transfer allowance.

## 14. Terminal output

FlowBrake also reports the simulation directly in the terminal. This is the same backend state that is visualized in the browser, so the project can be demonstrated without relying only on the frontend.

Each simulation tick prints:
- sender rate
- receiver-advertised window
- accepted packets
- drained packets
- limited packets
- receiver buffer usage and pressure
- brake level (NORMAL, MODERATE, HIGH, or CRITICAL)
- actual file-transfer progress

Example:

```text
TICK 012 | Sender= 60 | Window= 35 | Accepted= 35 | Drained= 10 | Limited= 25 | Buffer= 75/100 | Pressure= 75.0% | Brake=HIGH
          -> High receiver pressure: sender is strongly limited.
          File progress:  42.0% (43,008/102,400 bytes)
```

The browser remains the visual demonstration layer, while the terminal provides a direct view of the simulation engine and its decisions.


## Terminal-only demo

You can demonstrate the core receiver-driven flow-control logic without opening the browser:

```bash
source venv/bin/activate
python simulator.py
```

The terminal demo shows three stages: **Baseline**, **Pressure**, and **Recovery**, including sender rate, advertised receiver window, accepted/limited packets, buffer pressure, brake state, and transfer progress.

To start the full web application instead:

```bash
source venv/bin/activate
python app.py
```

Then open `http://127.0.0.1:5000`. The web simulation also prints its live results in the same terminal.
