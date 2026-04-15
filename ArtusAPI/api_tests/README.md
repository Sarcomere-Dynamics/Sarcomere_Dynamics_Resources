# ArtusAPI internal tests

These tests use **mocks only** (no serial, no hand). They are meant for local or CI use.

## Run from repository root

```bash
cd /path/to/Sarcomere_Dynamics_Resources
PYTHONPATH=. python3 -m unittest discover -s ArtusAPI/api_tests -p "test_*.py" -v
```

With pytest (optional):

```bash
pip install pytest
PYTHONPATH=. python3 -m pytest ArtusAPI/api_tests -v
```

## Not publishing to GitHub

To keep this folder out of a public clone, add to the repo `.gitignore`:

```
ArtusAPI/api_tests/
```

Remove that line if you choose to publish tests later.
