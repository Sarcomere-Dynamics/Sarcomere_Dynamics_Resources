# Configuration Example

This folder holds the working `robot_config.yaml` used when you run examples from a repository checkout. The loader itself lives in the package as `ArtusAPI.configuration.ArtusConfig` and ships with the PyPI distribution.

## Files

- `robot_config.yaml`: Example configuration for left/right hand robots and logging. Edit this file when running examples from this repo.
- `configuration.py`: Thin re-export of `ArtusConfig` for older `from examples.config.configuration import ArtusConfig` imports.

## How it works

1. `ArtusConfig` loads the YAML file into a nested `SimpleNamespace`.
2. In a checkout it prefers this folder's `robot_config.yaml`. After `pip install artusapi`, pass a path, set `ARTUS_CONFIG`, put `robot_config.yaml` in the working directory, or copy the packaged template with `copy_default_config()`.

## Typical usage

```python
from ArtusAPI import ArtusConfig

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

- In this repo the default config path is `examples/config/robot_config.yaml`.
- `check_and_print_robot_config()` is a quick helper to print per-hand settings.