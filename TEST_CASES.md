# FlowBrake Test Cases

| ID | Sender | Drain | Buffer | Adaptive | Expected |
|---|---:|---:|---:|---|---|
| TC01 | 20 | 20 | 100 | ON | Stable/low buffer |
| TC02 | 60 | 10 | 100 | ON | Buffer rises, brake strengthens |
| TC03 | 60 | 40 | 100 | ON | Buffer eventually falls |
| TC04 | 60 | 10 | 100 | OFF | Window follows free buffer |
| TC05 | 80 | 0 | 50 | ON | Critical braking / near full buffer |
| TC06 | 10 | 30 | 100 | ON | Buffer remains near zero |

## Viva validation

**Q: What controls the sender?**  
A: Receiver feedback through the advertised window.

**Q: Why is it receiver-driven?**  
A: The receiver determines and communicates how much data it can currently accept.

**Q: Is FlowBrake replacing TCP?**  
A: No. It is a simulation demonstrating the receive-window idea plus an experimental adaptive policy.

**Q: What happens when the buffer fills?**  
A: The advertised/effective sending allowance becomes smaller, so the sender is restricted.

**Q: What happens when the receiver becomes faster?**  
A: The buffer drains, free space increases, and the advertised window can increase.
