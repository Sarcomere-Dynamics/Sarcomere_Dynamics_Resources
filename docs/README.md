# Extra documentation (`docs/`)

The main [repository README](../README.md) is the **starting point** for setup, safety, and first motion. This folder holds **supplementary** markdown that goes deeper on specific topics.

## Files

| Document | What it covers |
|----------|----------------|
| [`API Functionality.md`](API%20Functionality.md) | `ArtusAPI_V2` usage notes (legacy `artus_api.py` is removed); read after you have run a basic example. |
| [`CLI.md`](CLI.md) | Command-line tooling related to the ecosystem (see the file for exact scope). |
| [`Flash CLI.md`](Flash%20CLI.md) | Firmware flashing from the command line—read before attempting field updates. |

## How to use this folder

1. Complete a **minimal hardware + software** bring-up using `examples/general_example/`.  
2. Skim **API Functionality** when function names make sense but the *why* is still fuzzy.  
3. Open **CLI / Flash CLI** only when you are deliberately performing maintenance tasks.

## Related

- [`ArtusAPI/README.md`](../ArtusAPI/README.md) — code layout inside the Python package  
- Model-specific hardware markdown files under `ArtusAPI/robot/<model>/`
