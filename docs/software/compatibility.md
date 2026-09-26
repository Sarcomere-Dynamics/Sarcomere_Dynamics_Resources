# Firmware / API Compatibility

This page tracks which hand firmware versions are compatible with which versions of `ArtusAPI` (v2, unless noted). Each hand has its own firmware and its own version numbering — they are **not** unified across models.

**Firmware is versioned by `<BUILD>.<CONTROL BOARD>.<ACTUATOR>`.**

For example, an ARTUS Lite Mk. 9 purchased in September 2026 may have its **control board flashed with the V9.13.XX** firmware, while its **actuators may run the corresponding V9.XX.15** firmware.

## How to read this

- **API Version** — the **artusapi** pip version, matching the [Revision Control table](/README.md#revision-control) in the root README.
- **Notes** — breaking changes, required migration steps, or a link to the changelog entry that explains the change.

Rows are sorted newest-first, same convention as Revision Control.

## ARTUS Lite / Lite+

| Mainboard Firmware Version | Compatible API Version(s) | Notes                                       |
| :----------------------------: | :-----------------------: | ------------------------------------------- |
|            vX.10.x+            |          v2.0.0+          | Updated communication, Cascaded PID Control |
|             vX.9.x             |          v1.X.X           | Legacy API                                  |

## ARTUS Talos

| Mainboard Firmware Version | Compatible API Version(s) | Notes                                                                                            |
| :----------------------------: | :-----------------------: | ------------------------------------------------------------------------------------------------ |
|               -                |          v2.0.0+          | Requires `calibrate()` on boot. See [ARTUS_TALOS.MD](/docs/hardware/artus_talos/artus_talos.md). |

## ARTUS Scorpion

| Mainboard Firmware Version | Compatible API Version(s) | Notes                                                                                                     |
| :----------------------------: | :-----------------------: | --------------------------------------------------------------------------------------------------------- |
|               -                |          v2.0.0+          | Requires `calibrate()` on boot. See [ARTUS_SCORPION.md](/docs/hardware/artus_scorpion/artus_scorpion.md). |

## ARTUS Dex

| Mainboard Firmware Version | Compatible API Version(s) | Notes |
| :----------------------------: | :-----------------------: | ----- |
|               -                |          v2.0.0+          | TBD   |
