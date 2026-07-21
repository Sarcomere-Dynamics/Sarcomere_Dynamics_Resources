# Flashing Masterboard Firmware with `upload_esptool.py`

`upload_esptool.py` flashes an ARTUS LITE masterboard **ESP32-S3** with a merged firmware binary using the [`esptool`](https://github.com/espressif/esptool) Python library directly — no `arduino-cli` or Arduino IDE install is required on the flashing machine.

The script only accepts a **merged binary**, that can be downloaded from the release package assets. 

## Prerequisites

* Python 3
* `esptool` installed:

```bash
pip install esptool
```

* A merged firmware binary (`*merged*.bin`). The script rejects any file that is not a `.bin` with `merged` in its name.
* The masterboard connected over USB and its serial port identified (e.g. `/dev/ttyUSB0` on Linux, `/dev/tty.usbserial-*` on macOS, `COM3` on Windows).

## Usage

```bash
python3 upload_esptool.py -p <serial_port> -f <merged_binary>
```

### Example

```bash
python3 upload_esptool.py -p /dev/ttyUSB0 -f /path/to/master.ino.merged.bin
```

## Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `-p`, `--port` | Yes | — | Serial port of the masterboard, e.g. `/dev/ttyUSB0`. |
| `-f`, `--file` | Yes | — | Path to the merged binary (e.g. `master.ino.merged.bin`). Must be a `*merged*.bin` file. |
| `--baud` | No | `921600` | Flashing baud rate. |
| `--chip` | No | `esp32s3` | Target chip. |
| `--erase` | No | off | Erase the entire flash before writing (adds `--erase-all`). |

## What it does

Under the hood the script assembles and runs an `esptool write_flash` command, writing the merged binary at offset `0x0`:

```bash
esptool --chip esp32s3 --port /dev/ttyUSB0 --baud 921600 \
  --before default_reset --after hard_reset \
  write_flash -z \
  --flash_mode keep --flash_freq keep --flash_size keep \
  0x0 master.ino.merged.bin
```

The exact command is printed to the console before flashing, so you can see precisely what is being run.

## Notes

* Use `--erase` when switching between significantly different firmware versions or if you suspect a corrupted flash. It clears the entire chip (including any stored NVS/calibration data) before writing.
* If flashing fails to connect, verify the port, that no other program is holding the serial connection, and try putting the board into bootloader/download mode.
* Power-cycle the hand after flashing so parameter changes take effect.
