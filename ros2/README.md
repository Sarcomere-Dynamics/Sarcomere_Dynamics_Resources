# ROS 2 integration

[ROS 2](https://docs.ros.org/) is a popular middleware for robotics: it standardizes **nodes**, **topics**, and **messages** so arms, cameras, and hands can be orchestrated together.

This repository includes a **workspace** that wraps ARTUS control for ROS 2 users. The detailed build and run instructions live next to the workspace because ROS versions and distro names change over time.

## Where to go next

- **[`artuslite_ws/README.md`](artuslite_ws/README.md)** — Primary ROS 2 workspace documentation (dependencies, build, launch patterns).

## Relationship to the Python API

The ROS node ultimately relies on the same underlying concepts as the Python examples: **connect**, **wake / calibrate as required**, then stream commands. If ROS is confusing, run [`examples/general_example/`](../examples/general_example/) once without ROS to separate “hand issues” from “middleware issues”.

**Heads-up:** The in-tree Python package no longer includes `artus_api.py`; it exports **`ArtusAPI_V2`** only. The `artuslite_ros_api` node may still reference the legacy class until that package is migrated—see [`artuslite_ws/README.md`](artuslite_ws/README.md).

## See also

- Main [repository README](../README.md)  
- [`ArtusAPI/README.md`](../ArtusAPI/README.md)
