# artusapi

![Banner](docs/assets/images/logo.svg)

**artusapi** is a Python API for controlling the Sarcomere Dynamics ARTUS family of robotic hands over RS485/Modbus RTU or TCP.

See the Sarcomere Dynamics Inc. [Software License](LICENSE) for terms and conditions of use.

For further technical support with usage, contact <info@sarcomeredynamics.com>.

## Table of Contents

- [Supported Hardware](#supported-hardware)
- [Installation](#installation)
- [Revision Control](#revision-control)

## Supported Hardware

> [!IMPORTANT]
> Each product in the ARTUS lineup by Sarcomere Dynamics has its own unique wiring, joint maps, and calibration requirements.
>
> Please review the documentation corresponding to your ARTUS hand before powering on the device.

| Product        | Calibration required | Hardware README                                                      |
| -------------- | -------------------- | -------------------------------------------------------------------- |
| ARTUS Lite     | No                   | [artus_lite.md](/docs/hardware/artus_lite/artus_lite.md)             |
| ARTUS Lite+    | No                   | [artus_lite_plus.md](/docs/hardware/artus_lite/artus_lite_plus.md)   |
| ARTUS Talos    | **Yes**              | [artus_talos.md](/docs/hardware/artus_talos/artus_talos.md)          |
| ARTUS Scorpion | **Yes**              | [artus_scorpion.md](/docs/hardware/artus_scorpion/artus_scorpion.md) |
| ARTUS Dex      | No                   | **WORK IN PROGRESS**                                                 |

## Installation

Stable releases of [**artusapi** are hosted on PyPi](https://pypi.org/project/artusapi/), and can be installed via **pip**.

```
$ pip install artusapi
```

Alternatively, **artusapi** may be installed via [**uv**](https://docs.astral.sh/uv/)

```
$ uv add artusapi
```

For the latest development version of **artusapi**, this repository may be cloned directly from GitHub.

## Revision Control

|     Date      | Revision |                     Changelog                      | Pip Release |
| :-----------: | :------: | :------------------------------------------------: | :---------: |
| Oct. 09, 2026 |   v3.0   |        [2026-10.md](/changelog/2026-10.md)         |    v3.0     |
| Jul. 20, 2026 |   v2.1   |        [2026-07.md](/changelog/2026-07.md)         |      -      |
| Dec. 31, 2025 |   v2.0   |        [2025-12.md](/changelog/2025-12.md)         |      -      |
| Jun. 02, 2025 | v1.3.10  |        [2025-06.md](/changelog/2025-06.md)         |   v1.3.10   |
| Apr. 22, 2025 |  v1.1.1  |           readmes/documentation updated            |      -      |
| Nov. 14, 2024 |   v1.1   |               firmware v1.1 release                |    v1.1     |
| Oct. 23, 2024 |  v1.0.2  | awake parameter added, wake up function in connect |   v1.0.1    |
| Oct. 09, 2024 |   v1.0   |                 ARTUS Lite Release                 |    v1.0     |
| Apr. 23, 2024 |  v1.1b   |           Beta release - ARTUS Lite Mk 6           |      -      |
| Nov. 14, 2023 |  v1.0b   |         Initial release - ARTUS Lite Mk 5          |      -      |
