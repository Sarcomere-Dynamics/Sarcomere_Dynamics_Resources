# Updating Actuator Firmware via the General Example

This guide covers flashing **actuator (brushless driver) firmware** on an ARTUS hand using the interactive [`general_example.py`](/examples/general_example/general_example.py) menu. The firmware binary is streamed to the driver(s) through the masterboard over the existing Modbus RTU/TCP connection — no extra tools are required.

> [!IMPORTANT]
> This is **not** the same as flashing the masterboard ESP32-S3. For that, see [UPLOAD_ESPTOOL.md](UPLOAD_ESPTOOL.md). This process updates the firmware running on the finger actuators / brushless drivers.

> [!WARNING]
> **DO NOT flash firmware unless instructed by the Sarcomere Dynamics team.** Interrupting a firmware update or flashing an incorrect binary can leave a driver in an unrecoverable state. The menu deliberately requires an extra confirmation before proceeding.

## Prerequisites

* The general example set up and running. See the [General Example README](/examples/general_example/README.md) for installing requirements, finding the USB device, and configuring [`robot_config.yaml`](/examples/config/robot_config.yaml).
* The correct actuator firmware `.bin` file, supplied by Sarcomere Dynamics. Note its absolute path.
* Know which driver(s) you need to flash (a specific actuator, or all of them).

## Procedure

1. Run the general example:

```bash
cd examples/general_example
python3 general_example.py
```

2. Connect to the hand — enter `1` at the menu.

3. Start the firmware update — enter `f` at the menu.

4. Confirm the safety prompt by entering `e` when asked. Any other input cancels.

5. Enter the **driver to flash** when prompted:

| Value | Meaning |
|---|---|
| `1`–`<number of controllers` | A specific actuator, mapped to its joint number |
| `0` | All actuators |

   The value is validated against the robot model's `number_of_controllers`; an out-of-range value is rejected and you can try again.

6. Enter the **absolute path** to the firmware `.bin` file when prompted (e.g. `/home/user/firmware/driver.bin`).

The upload then begins. A progress bar (`Uploading Actuator Firmware`) shows pages as they are written, and the tool waits for the hand to acknowledge the flash. When the hand leaves the `ACTUATOR_FLASHING` state the update is complete and `Firmware flashed successfully` is logged.

## What happens under the hood

The `f` handler in `handle_command()` calls:

```python
artusapi.update_firmware(file_location=file_location_, drivers_to_flash=driver)
```

`ArtusAPI_V2.update_firmware()` (in [`artus_api_new.py`](/ArtusAPI/artus_api_new.py)) then:

1. Reads the binary size via `FirmwareUpdaterNew.get_bin_file_info()`.
2. Sends the firmware command (with the selected driver) to the command register.
3. Streams the binary to the masterboard in 128-byte half-page chunks using [`FirmwareUpdaterNew.update_firmware()`](FirmwareUpdaterNew.py), waiting for the initial flashing acknowledgment before starting and sending a terminating `[0x0, 0x0]` chunk when done.
4. Polls `get_robot_status()` until the hand is no longer in the `ACTUATOR_FLASHING` state.

## Troubleshooting

* **The update stalls at the start** — the hand never sent a flashing acknowledgment (`flashing_ack_checker` returns `False`). Verify the connection is healthy and that the hand is in an idle/ready state before pressing `f`.
* **`Invalid driver number`** — the driver you entered exceeds the number of controllers on the connected hand. Re-enter a valid value.
* **The hand reports an error state** — flashing failed. Do not power-cycle mid-flash; contact the Sarcomere Dynamics team.
* Power-cycle the hand after a successful update if parameter changes are expected to take effect.
