# Configuration Example

This folder shows how to drive the Artus APIs from a YAML config file. The main entry point is `configuration.py`, which loads `robot_config.yaml`, converts it into a `SimpleNamespace`, and returns the appropriate API object based on which robot is connected.

## Files

- `configuration.py`: Loads config, selects the connected robot, and returns `ArtusAPI` or `ArtusAPI_V2`.
- `robot_config.yaml`: Example configuration for left/right hand robots and logging.

## How it works

1. `ArtusConfig` loads the YAML file into a nested `SimpleNamespace`.

## Typical usage

```python
from examples.config.configuration import ArtusConfig

config = ArtusConfig()
api = config.get_api()

if config.get_robot_calibrate():
    api.calibrate()

if config.get_robot_wake_up():
    api.wake_up()
```

## Configuration fields

Edit [`robot_config.yaml`](robot_config.yaml) and set the fields for each robot. Common fields:

- `robot_connected`: `true` for the single connected robot.
- `robot_type`: e.g. `artus_talos`, `artus_scorpion`, `artus_lite`.
- `communication_method`: e.g. `RS485_RTU`, `UDP`, `WiFi`.
- `communication_channel_identifier`: Port or address (e.g. `/dev/ttyUSB0`).
- `hand_type`: `left` or `right`.
- `start_robot`: Whether to wake on start.
- `reset_on_start`: Reset flag (int).
- `streaming_frequency`: Data rate in Hz.
- `calibrate`: Whether to run calibration on start.

> [!NOTE]
> Calibrate and start_robot fields are not used for the general_example.py as they are options in the menu

## Notes

- The default config path is `examples/config/robot_config.yaml`.
- `configuration.py` prints the detected project root on import.
- `check_and_print_robot_config()` is a quick helper to print per-hand settings.