# Robot models (`ArtusAPI/robot`)

This folder holds **one subfolder per supported hand**, plus a shared base class. Each hand subfolder tells the rest of the library **how many joints exist, what they are called, and how they map to the physical hardware**.

You do not need to memorize every joint name on day one. What matters for onboarding:

1. Pick the **`robot_type`** string your program uses (see the [reference table](#robot_type--hand_type-reference) below). That string is how `Robot` in [`robot.py`](robot.py) selects the correct class.
2. Pick **`hand_type`** (`left`/`right`) when the model has distinct left and right variants.
3. Read the **markdown datasheet** for your hardware if you are doing wiring, calibration, or troubleshooting LEDs.

## Subfolders

| Folder | What it represents |
|--------|---------------------|
| [`artus_lite/`](artus_lite/) | ARTUS Lite and ARTUS Lite+ (Plus adds Contactile force sensors; same folder, separate classes). |
| [`artus_talos/`](artus_talos/) | ARTUS Talos. |
| [`artus_scorpion/`](artus_scorpion/) | ARTUS Scorpion (single-DOF parallel gripper — no left/right). |
| [`artus_dex/`](artus_dex/) | ARTUS Dex (left/right). No hardware datasheet yet — see [`artus_dex.py`](artus_dex/artus_dex.py) as the source of truth in the meantime. |
| [`bldc_robot/`](bldc_robot/) | `BLDCRobot` — the shared base class every hand above inherits from (joint definitions, angle constraints, `set_joint_angles`/`get_joint_angles` plumbing). Not a standalone hand; nothing instantiates this folder directly. Its markdown ([`BDLC_Robot.md`](bldc_robot/BDLC_Robot.md)) documents the physical BLDC driver board used specifically by **Talos, Scorpion and Dex** — Lite uses a different actuator hardware even though they share this same Python base class. |

## `robot_type` / `hand_type` reference

This is the exact string pairing [`robot.py`](robot.py)'s factory (and `examples/config/robot_config.yaml`) expects. Anything else raises `ValueError("Unknown robot type")` or `ValueError("Unknown hand")`.

| `robot_type` | Valid `hand_type` | Class instantiated |
|---|---|---|
| `artus_lite` | `left`, `right` | `ArtusLite_LeftHand` / `ArtusLite_RightHand` |
| `artus_lite_plus` | `left`, `right` | `ArtusLite_Plus_LeftHand` / `ArtusLite_Plus_RightHand` |
| `artus_talos` | `left`, `right` | `ArtusTalos_Left` / `ArtusTalos_Right` |
| `artus_scorpion` | ignored | `ArtusScorpion` |
| `artus_dex` | `left`, `right` | `ArtusDex_Left` / `ArtusDex_Right` |

## Model-specific documentation

Inside several model folders you will find standalone markdown files (joint maps, electrical notes, LED meanings). Those are the **source of truth** for hardware detail; this README only orients you.

Start from the main [repository README](../../README.md) section [Supported Hardware](../../README.md#supported-hardware) for direct links.

## Mental model

Think of each robot class as a **dictionary of joints** plus **rules** the API uses when packing commands and interpreting feedback. Changing robot type changes both **how many numbers** you send and **what each index means**.
