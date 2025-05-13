# !/bin/bash
# esptool sh file

# Sarcomere Dynamics Software License Notice
# ------------------------------------------
# This software is developed by Sarcomere Dynamics Inc. for use with the ARTUS family of robotic products,
# including ARTUS Lite, ARTUS+, ARTUS Dex, and Hyperion.

# Copyright (c) 2023–2025, Sarcomere Dynamics Inc. All rights reserved.

# Licensed under the Sarcomere Dynamics Software License.
# See the LICENSE file in the repository for full details.

esptool.py --chip esp32s3 --port $1 --baud 921600  --before default_reset --after hard_reset write_flash  -z --flash_mode keep --flash_freq keep --flash_size keep 0x0 "bins/master.bootloader.bin" 0x8000 "bins/master.partitions.bin" 0xe000 "bins/boot_app0.bin" 0x10000 "bins/master.bin"