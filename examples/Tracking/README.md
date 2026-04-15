# Tracking examples

This folder contains **support code for hand tracking experiments**: reading data from gloves or other trackers, filtering it, and sometimes displaying it in a small UI. It is **more fragmented** than `general_example/` because each vendor or protocol has its own quirks.

If you are not building a tracking-based demo yet, you can skip this folder until you need it.

## What you might find here

| Area | Purpose |
|------|---------|
| [`manus_gloves_data/`](manus_gloves_data/) | Sample code and calibration-style data for Manus glove workflows. |
| [`manus_finger_tip_data/`](manus_finger_tip_data/) | Finger-tip oriented processing and related C++ client stubs. |
| [`zmq_class/`](zmq_class/) | Messaging helpers (for example ZeroMQ) when tracking runs in a separate process. |
| [`ui/`](ui/) | Lightweight UI modules used by some tracking demos. |
| [`hand_tracking_data.py`](hand_tracking_data.py) | Glue logic at the tracking layer (inspect the file to see what it expects as inputs). |

## How this relates to teleoperation

[Teleoperation](../Teleoperation/) examples usually **consume** tracking-like data and **call the ARTUS API**. This folder is often where **raw sensor handling** or **IPC** lives before that step.

## Expectations

- You may need **vendor SDKs**, **specific Python versions**, or **system libraries** not listed in the base API requirements.  
- Treat scripts here as **starting points**: verify units (degrees vs radians), joint ordering, and rate limits before connecting to hardware.

## See also

- [Examples README](../README.md)  
- [Teleoperation README](../Teleoperation/README.md)
