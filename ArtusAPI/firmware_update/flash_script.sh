# !/bin/bash
# esptool sh file
esptool.py --chip esp32s3 --port $1 --baud 921600  --before default_reset --after hard_reset write_flash  -z --flash_mode keep --flash_freq keep --flash_size keep 0x0 "bins/master.ino.bootloader.bin" 0x8000 "bins/master.ino.partitions.bin" 0xe000 "bins/boot_app0.bin" 0x10000 "bins/master.ino.bin"