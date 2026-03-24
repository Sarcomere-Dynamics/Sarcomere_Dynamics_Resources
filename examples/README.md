# Examples

The `examples` folder contains **small, runnable programs** that show how to connect to an ARTUS hand and do something useful: move fingers, open a GUI, or stream poses from a camera or glove.

If you are new here, treat this folder as a **cookbook**, not as a second product. Always align with the **hardware you own** and the **startup sequence** in the main [repository README](../README.md).

## Suggested first steps

1. **[`general_example/`](general_example/)** — Minimal “connect, wake, command” flow. Read its README and run it once with hardware on a bench.
2. **[`config/`](config/)** — Same idea, but settings (port, robot type, hand side) live in a YAML file. Good once you understand the basic flow.
3. **[`GUI/`](GUI/)** — Desktop UI for interactive testing.

## Example index

| Path | What it demonstrates | README |
|------|----------------------|--------|
| [`general_example/`](general_example/) | Basic API usage | [README](general_example/README.md) |
| [`config/`](config/) | YAML-driven configuration | [README](config/README.md) |
| [`GUI/`](GUI/) | Graphical controller | [README](GUI/README.md) |
| [`urarm_rs485_example/`](urarm_rs485_example/) | RS485 use with a UR robot arm setup | [README](urarm_rs485_example/README.md) |
| [`UR_PortForward/`](UR_PortForward/) | Bridging network serial to a local pseudo-TTY (see folder README) | [README](UR_PortForward/README.md) |
| [`Teleoperation/`](Teleoperation/) | Human-in-the-loop control (glove, camera) | [README](Teleoperation/README.md) |
| [`Tracking/`](Tracking/) | Hand tracking pipelines and UI glue code | [README](Tracking/README.md) |
| [`deprecated/`](deprecated/) | Older scripts kept for reference | [README](deprecated/README.md) |

## Dependencies

Some examples need **extra Python packages** (OpenCV, Qt, vendor SDKs, and so on). Each subfolder’s README or local `requirements.txt` is authoritative. When unsure, create a **virtual environment** and install only what that example needs.

## Safety and expectations

Examples assume you understand **power limits**, **pinch hazards**, and **emergency stop** practices for your lab. They are teaching aids: review and adapt them before using them around people or valuable equipment.
