# ArtusAPI internal tests

These tests use **mocks only** (no serial, no hand). They are meant for local or CI use.

## Run from repository root

```bash
cd /path/to/Sarcomere_Dynamics_Resources
PYTHONPATH=. python3 -m unittest discover -s artusapi/tests -p "test_*.py" -v
```

With pytest (optional):

```bash
pip install pytest
PYTHONPATH=. python3 -m pytest artusapi/tests -v
```
