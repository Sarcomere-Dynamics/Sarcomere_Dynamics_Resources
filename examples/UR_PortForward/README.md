# UR port forwarder example

Some setups expose the hand’s serial service **over the network** (for example when the hand is wired through a Universal Robots controller or similar gateway). Your laptop, however, may expect a **local serial device** such as `/dev/ttyUSB0`.

This example uses **`socat`** to create a **pseudo-terminal on your machine** that forwards bytes to a **TCP port** on the robot side. From Python’s point of view, you still open a serial port—but that port is actually bridged over Ethernet.

## Files

- [`artus_api_port_forwarder.py`](artus_api_port_forwarder.py) — Helper class that starts the bridge and returns the local device name.

## Prerequisites

- `socat` installed on the host that runs the script.  
- Network reachability from your PC to the configured robot IP.  
- Permission to create the pseudo-TTY path (the default in code is under `/tmp`).

## Mental model

```
[ Python / ArtusAPI_V2 ] → [ local PTY ] --socat--TCP--> [ robot:port ]
```

You point `communication_channel_identifier` (or equivalent) at the **local** device name returned by the forwarder, not at the remote IP directly.

## Related reading

- [Examples index](../README.md)  
- Main [repository README](../../README.md) for communication options and safety
