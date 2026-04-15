# ArtusAPI (Python library)

This folder is the **Python control library** for ARTUS robotic hands from Sarcomere Dynamics. If you are new to robotics, think of it as a **driver plus a small toolkit**: your program imports this code, opens a connection to the hand, then sends targets (for example “move this finger to 30 degrees”) and reads back state (positions, errors, and similar feedback).

The hardware still needs correct **power, cabling, and safety practices**. Software cannot replace reading the main [repository README](../README.md) and the product-specific notes linked there.

## What you actually import

The package exports **`ArtusAPI_V2`** from [`__init__.py`](__init__.py). Implementation lives in [`artus_api_new.py`](artus_api_new.py).

The legacy module **`artus_api.py` is no longer in this repository.** Older tutorials that used `from ArtusAPI.artus_api import ArtusAPI` should be updated to `ArtusAPI_V2` and the constructor / communication options that match your hardware.

```python
from ArtusAPI import ArtusAPI_V2
```

Your application chooses parameters such as **robot type**, **left or right hand**, and **how the PC talks to the device** (for example RS485). Those details are set when you construct the API object or via a config helper—see [examples/config/README.md](../examples/config/README.md).

## How the code is organized

| Folder | Role in plain terms |
|--------|---------------------|
| [`robot/`](robot/) | Descriptions of each supported hand: joint counts, names, limits, and model-specific behavior. Start with [robot/README.md](robot/README.md). |
| [`communication/`](communication/) | Transports (serial, RS485, Ethernet, UDP, WiFi, UART). This is where bytes move between your PC and the hand’s electronics. |
| [`commands/`](commands/) | Building and encoding the low-level command streams the firmware understands. |
| [`common/`](common/) | Shared definitions such as register maps used across transports. |
| [`firmware_update/`](firmware_update/) | Tools and assets related to updating hand firmware from Python. |
| [`sensors/`](sensors/) | Optional sensor-related helpers used by some setups. |

Legacy and new implementations may coexist while products evolve; when in doubt, follow the **example that matches your hand model** under [`examples/`](../examples/).

## Dependencies

- Primary dependency list for current work: [`requirements_v2.txt`](../requirements_v2.txt) at the repository root (also see [`requirements.txt`](../requirements.txt) if you maintain older scripts).

## Related reading

- [Repository README](../README.md) — setup, power-up sequence, safety context  
- [docs/README.md](../docs/README.md) — deeper notes on API behavior and CLI tools  
- Model-specific hardware notes inside each `robot/<model>/` folder (for example `ARTUS_LITE.md`, `ARTUS_TALOS.MD`, `ARTUS_SCORPION.md`)
