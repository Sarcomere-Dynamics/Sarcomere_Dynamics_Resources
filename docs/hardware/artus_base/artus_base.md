# Artus BLDC Driver

![Sarcomere Dynamics Inc. Logo](/docs/assets/images/logo.svg)

The following document provides information on the core of our new products, the ARTUS Brushless DC (BLDC) motor driver.
This information pertains to the following systems:

- [Artus Scorpion](/docs/hardware/artus_scorpion/artus_scorpion.md)
- [Artus Talos](/docs/hardware/artus_talos/artus_talos.md)
- [Artus Dex](<>)

## Startup

All systems using the ARTUS BLDC Driver require the following steps every time the system is powered on.

1. Send a `wake_up` command. This tells the drivers to do an electrical calibration for proper commutation.
2. Send a `calibrate` command. This tells the drivers to do an mechanical end-stop calibration based on the respective system. It will then drive itself back to the start position.

## Cascaded PID Control

The system uses the following closed-loop, cascaded PID control scheme.
This allows for position, velocity and torque control.
For fingered systems, the joint targets are in the following units:

- Position : degrees
- Velocity : degrees/s
- Force : Newtons (N)

<div align=center>
<img src='data/Cascading_PID.png' width=800>
</div>
