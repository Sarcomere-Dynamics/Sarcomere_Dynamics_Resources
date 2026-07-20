# Firmware / API Compatibility

This page tracks which hand firmware versions are compatible with which versions of `ArtusAPI` (v2, unless noted). Each hand has its own firmware and its own version numbering — they are **not** unified across models.

>[!IMPORTANT]
>This table is maintained by hand. When you ship a firmware or API release that changes compatibility, add a row here in the same commit/PR — see [Keeping this page up to date](#keeping-this-page-up-to-date).

## How to read this

* **API version** — the `ArtusAPI` pip version, matching the [Revision Control table](../README.md#revision-control) in the root README.
* **Notes** — breaking changes, required migration steps, or a link to the changelog entry that explains the change.

Rows are sorted newest-first, same convention as Revision Control.

## Artus Lite / Lite+

| Firmware version | Compatible API version(s) | Notes |
|---|---|---|
| v9.x | v1.x | legacy api |
| v10.x | v2.1 | v2, pos, vel and force control |

## Artus Talos

| Firmware version | Compatible API version(s) | Notes |
|---|---|---|
| TBD | TBD | TBD — requires `calibrate()`; see [ARTUS_TALOS.MD](/ArtusAPI/robot/artus_talos/ARTUS_TALOS.MD) |

## Artus Scorpion

| Firmware version | Compatible API version(s) | Notes |
|---|---|---|
| TBD | TBD | TBD — requires `calibrate()`; see [ARTUS_SCORPION.md](/ArtusAPI/robot/artus_scorpion/ARTUS_SCORPION.md) |

## Artus Dex

| Firmware version | Compatible API version(s) | Notes |
|---|---|---|
| TBD | TBD | TBD |

## Keeping this page up to date

* Add a row whenever a firmware or API release changes what's compatible with what — don't wait for a separate "docs pass."
* If a change is breaking (old firmware no longer works with new API, or vice versa), say so explicitly in **Notes** and link the relevant [changelog](../changelog/) entry.
* If a hand's firmware and API have only ever shipped together with no version skew yet, a single row is fine (e.g. "all versions to date").
