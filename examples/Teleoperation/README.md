# Teleoperation examples

**Teleoperation** means a human moves, and the robot hand **follows** in real time (often with smoothing and scaling). This folder contains sample integrations that connect **human pose sources** to the ARTUS API.

You should already be comfortable with the basic connect / wake / command flow from [`general_example/`](../general_example/) before running these.

## What is in this folder

| Subfolder | Idea in plain language | README |
|-----------|-------------------------|--------|
| [`ManusGloveControl/`](ManusGloveControl/) | Data gloves feed finger poses into the hand. | [README](ManusGloveControl/README.md) |
| [`GoogleMediaPipeControl/`](GoogleMediaPipeControl/) | A webcam tracks hand landmarks; those landmarks drive joint targets. | [README](GoogleMediaPipeControl/README.md) |

## Typical pipeline

1. **Sense** — Camera or glove produces a stream of numbers (joint angles or 3D points).  
2. **Map** — Your code converts those numbers into **ARTUS joint targets** (often with limits so you do not command impossible poses).  
3. **Act** — The API sends commands at a steady rate (similar to a video game loop).

Latency, calibration, and hand dominance (left vs right) all matter. Expect to tune scaling factors.

## Related material

- [Examples index](../README.md)  
- [Tracking examples](../Tracking/) — lower-level tracking utilities and UI pieces you might combine with teleoperation
