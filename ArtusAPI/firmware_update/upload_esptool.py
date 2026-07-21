#!/usr/bin/env python3
"""Flash an ARTUS masterboard ESP32-S3 with a merged firmware binary.

Uses the esptool Python library directly (``pip install esptool``), so no
arduino-cli or Arduino IDE install is required on the flashing machine.

Only accepts a merged binary (e.g. ``master.ino.merged.bin`` produced by
``arduino-cli compile --export-binaries``) - a single image that already
contains the bootloader, partition table, boot_app0 and app at their
correct offsets, flashed in one shot at offset 0x0.

Example:
  python3 upload_esptool.py -p /dev/ttyUSB0 -f /path/to/master.ino.merged.bin
"""
import argparse
import sys
from pathlib import Path

import esptool

DEFAULT_CHIP = "esp32s3"
DEFAULT_BAUD = 921600
MERGED_BIN_ADDR = "0x0"


def build_write_flash_args(args, merged_bin: Path):
    flash_args = [
        "--chip", args.chip,
        "--port", args.port,
        "--baud", str(args.baud),
        "--before", "default_reset",
        "--after", "hard_reset",
        "write_flash",
        "-z",
    ]
    if args.erase:
        flash_args.append("--erase-all")
    flash_args += [
        "--flash_mode", "keep",
        "--flash_freq", "keep",
        "--flash_size", "keep",
        MERGED_BIN_ADDR, str(merged_bin),
    ]
    return flash_args


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-p", "--port", required=True, help="Serial port, e.g. /dev/ttyUSB0")
    parser.add_argument(
        "-f", "--file", required=True,
        help="Path to the merged binary (e.g. master.ino.merged.bin)",
    )
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD)
    parser.add_argument("--chip", default=DEFAULT_CHIP)
    parser.add_argument("--erase", action="store_true", help="Erase entire flash before writing")
    args = parser.parse_args()

    merged_bin = Path(args.file)
    if not merged_bin.is_file():
        sys.exit(f"File not found: {merged_bin}")
    if merged_bin.suffix != ".bin" or "merged" not in merged_bin.name:
        sys.exit(
            f"{merged_bin.name} does not look like a merged binary "
            "(expected a '*merged*.bin' file, e.g. master.ino.merged.bin)."
        )

    flash_args = build_write_flash_args(args, merged_bin)
    print("esptool " + " ".join(flash_args))
    esptool.main(flash_args)


if __name__ == "__main__":
    main()
