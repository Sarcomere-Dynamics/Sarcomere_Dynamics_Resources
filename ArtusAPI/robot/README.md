# Robot models (`ArtusAPI/robot`)

This folder holds **one subfolder per supported hand (or platform)**. Each subfolder tells the rest of the library **how many joints exist, what they are called, and how they map to the physical hardware**.

You do not need to memorize every joint name on day one. What matters for onboarding:

1. Pick the **robot type** string your program uses (for example `artus_lite`, `artus_talos`, `artus_scorpion`, `artus_dex`). That string is how `Robot` in [`robot.py`](robot.py) selects the correct class.
2. Pick **left** or **right** when the model has distinct left and right variants.
3. Read the **markdown datasheet** for your hardware if you are doing wiring, calibration, or troubleshooting LEDs.

## Subfolders

| Folder | What it represents |
|--------|---------------------|
| [`artus_lite/`](artus_lite/) | ARTUS Lite family (including Plus variants where applicable). |
| [`artus_talos/`](artus_talos/) | ARTUS Talos. |
| [`artus_scorpion/`](artus_scorpion/) | ARTUS Scorpion. |
| [`artus_dex/`](artus_dex/) | ARTUS Dex (left/right). |
| [`bldc_robot/`](bldc_robot/) | Shared BLDC-oriented robot description used in some code paths. |

## Model-specific documentation

Inside several model folders you will find standalone markdown files (joint maps, electrical notes, LED meanings). Those are the **source of truth** for hardware detail; this README only orients you.

Start from the main [repository README](../../README.md) section **Robot Specific READMEs** for direct links.

## Mental model

Think of each robot class as a **dictionary of joints** plus **rules** the API uses when packing commands and interpreting feedback. Changing robot type changes both **how many numbers** you send and **what each index means**.
