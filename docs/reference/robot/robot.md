# Reference: robot/

## Base Class

[`ArtusBase`](/artusapi/robot/artus_base/) is the shared base class every hand above inherits from.
Every child class of `ArtusBase` must specify paramters such as joint definitions, angle constraints, or specific implementations of `ArtusAPI` methods.

## Child Classes

[`robot.py`](/artusapi/robot/robot.py) and `examples/config/robot_config.yaml`.
Anything else raises `ValueError("Unknown robot type")` or `ValueError("Unknown hand")`.

| `robot_type`      | Valid `hand_type` | Class                                                                    |
| ----------------- | ----------------- | ------------------------------------------------------------------------ |
| `artus_lite`      | `left`, `right`   | [`ArtusLiteLeft`, `ArtusLiteRight`](/artusapi/robot/artus_lite/)         |
| `artus_lite_plus` | `left`, `right`   | [`ArtusLitePlusLeft`, `ArtusLitePlusRight`](/artusapi/robot/artus_lite/) |
| `artus_talos`     | `left`, `right`   | [`ArtusTalosLeft`, `ArtusTalosRight`](/artusapi/robot/artus_talos/)      |
| `artus_scorpion`  | ignored           | [`ArtusScorpion`](/artusapi/robot/artus_scorpion/)                       |
| `artus_dex`       | `left`, `right`   | [`ArtusDex_Left`, `ArtusDex_Right`](/artusapi/robot/artus_dex/)          |
