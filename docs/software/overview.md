# Introduction to artusapi

The following document provides an introduction to the software implementation of **artusapi** and recommended practices for application development.

## Overview

> [!WARNING]
> All ARTUS products require correct **power, cabling, and safety practices**.
> Please review the product-specific documentation located in the [top-level README](/README.md) before attempting to use any applications involving artusapi.

The package exports the **`ArtusAPI`** and **`ArtusConfig`** base classes.

Their implementations can be found in [`artusapi.py`](/artusapi/artusapi.py) and [`configuration.py`](/artusapi/configuration.py) respectively.

An application using **artusapi** begins by listing parameters that define how the host will interact with the ARTUS product, including but not limited to:

- Communication Method: The host-device communication protocol (e.g., RS485_RTU, ModbusTCP)
- Robot Type: The selected ARTUS product (e.g. ARTUS Lite, ARTUS Talos, ARTUS Scorpion)
- Hand Type: Left or Right

These parameters are set when instantiating an **ArtusAPI** object, or passing a `robot_config.yaml` into an **ArtusConfig** object — see [examples/config/README.md](/examples/config/README.md) for more information.

## API Structure

For more details on the individual modules that comprise **artusapi**, please refer to the module-specific documentation.

| File                                             | Description                                                                                                                                  |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| [`artusapi.py`](/artusapi/artusapi.py)           | Defines the **ArtusAPI** class, which handles all interactions with the ARTUS product of interest.                                           |
| [`configuration.py`](/artusapi/configuration.py) | Defines the **ArtusConfig** class, which can be used to load configuration information via a YAML file to generate an **ArtusAPI** instance. |

| Directory                                        | Description                                                                                                                        |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| [`commands/`](/artusapi/commands/)               | Low-level Modbus commands for invoking actions from the control board.                                                             |
| [`common/`](/artusapi/common/)                   | Shared definitions used across transports: the Modbus register map (`ModbusMap.py`) and per-hand slave ID table (`SlaveIDMap.py`). |
| [`communication/`](/artusapi/communication/)     | RS485 RTU and Modbus TCP transports for host-to-hand communication                                                                 |
| [`firmware_update/`](/artusapi/firmware_update/) | Tools for updating **control board** and **actuator** firmware.                                                                    |
| [`robot/`](/artusapi/robot/)                     | Software definitions for each supported hand.                                                                                      |
| [`sensors/`](/artusapi/sensors/)                 | `ForceSensor` — the fingertip/Contactile force reading structure used by Talos, Scorpion, and Lite+.                               |

## Next steps: Usage

[Instructions on how to interact with an ARTUS product via an **ArtusAPI** object can be found in the next document](/docs/software/usage/usage.md)
