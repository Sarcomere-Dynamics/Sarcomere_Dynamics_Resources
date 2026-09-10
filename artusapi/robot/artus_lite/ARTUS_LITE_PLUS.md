<img src='../../../data/images/SarcomereLogoHorizontal.svg'>

# Artus Lite+

Mechanically identical to the [ARTUS Lite](ARTUS_LITE.md) — same power requirements, communication methods, startup/shutdown procedure, joint map, joint limits, and default speed/force values. **This file only covers what's different.** See [ARTUS_LITE.md](ARTUS_LITE.md) for everything else, and the [main repository README](/README.md) / [API Functionality](/docs/API%20Functionality.md) for general API usage.

## Table of Contents
* [Introduction](#introduction)
* [Difference Between Artus Lite and Artus Lite+](#difference-between-artus-lite-and-artus-lite)
* [Feedback Data Differences](#feedback-data-differences)

## Introduction
The Artus Lite+ has the same basic control and characteristics as the Artus Lite. However, it is equipped with fingertip force sensors. Here are the sensors that have been integrated to date:

* Contactile — Data integrated

## Difference Between Artus Lite and Artus Lite+
Mechanically, there is no difference between the two hands — the sole difference is the feedback data and fingertip sensors.

## Feedback Data Differences
* Artus Lite+ also outputs the x, y, z vector forces from the 5 fingertips instead on top of the other general feedback telemetry data consistent with the Artus Lite.
