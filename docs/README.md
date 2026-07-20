# Extra documentation (`docs/`)

The main [repository README](../README.md) is the **starting point** for setup, safety, and first motion. This folder holds **supplementary** markdown that goes deeper on specific topics.

## Files

| Document | What it covers |
|----------|----------------|
| [`API Functionality.md`](API%20Functionality.md) | `ArtusAPI_V2` usage notes (legacy `artus_api.py` is removed); read after you have run a basic example. |
| [`COMPATIBILITY.md`](COMPATIBILITY.md) | Which hand firmware versions work with which `ArtusAPI` versions—check before updating either. |

## How to use this folder

1. Complete a **minimal hardware + software** bring-up using `examples/general_example/`.  
2. Skim **API Functionality** when function names make sense but the *why* is still fuzzy.  
3. Check **COMPATIBILITY** before updating firmware or the API package.  

## Related

- [`ArtusAPI/README.md`](../ArtusAPI/README.md) — code layout inside the Python package  
- Model-specific hardware markdown files under `ArtusAPI/robot/<model>/`
