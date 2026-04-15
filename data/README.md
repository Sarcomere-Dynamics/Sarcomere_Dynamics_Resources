# Data assets

This folder holds **non-code files** used by documentation and some examples: images for the main README, and **saved hand poses** you can load in software.

## `images/`

Pictures and diagrams (for example wiring or marketing logos) referenced from markdown in the repository. They are not loaded at runtime by the API unless an example explicitly points to them.

## `hand_poses/`

JSON files describing **finger joint configurations**—think of them as **named snapshots** like “open hand”, “pinch”, or test trajectories.

Typical uses:

- Seeding a demo with a known-safe pose.  
- Recording and replaying a short motion during bring-up.  
- Regression testing UI or scripting without a human operator.

The exact **joint order and units** in each file must match the **robot model** you use. When unsure, compare a JSON file against the joint list in the model-specific documentation under [`ArtusAPI/robot/`](../ArtusAPI/robot/README.md).

## See also

- [Repository README](../README.md)  
- [Examples README](../examples/README.md)
