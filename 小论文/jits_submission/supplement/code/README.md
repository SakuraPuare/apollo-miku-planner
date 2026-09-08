# MIKU evaluation code

This directory contains the deterministic scenario generators, planning
pipeline, metric implementation, protocol runners, and tests used by the
accompanying manuscript. It is a small `uv` project with Python 3.12 or
newer as specified in `pyproject.toml`.

From this directory, install the locked environment and run the focused test
suite with:

```bash
uv sync --locked
PYTHONPATH=可视化 uv run pytest -q tests
```

The generated data consumed by the manuscript is kept one level above this
directory in `../data/小论文-2/generated/`. The protocol runners write to a
caller-supplied output directory and do not overwrite the frozen files unless
explicitly directed to do so.
