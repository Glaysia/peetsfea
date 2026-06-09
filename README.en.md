---
title: peetsfea
created: 2026-04-17 @ 09:09
updated: 2026-06-01 @ 00:00
tags:
  - governance
---

# peetsfea

peetsfea is a Python project for deterministic HFSS (AEDT) design generation from TOML specs.

The 0.3.0 baseline removes the accumulated geometry generation implementation and keeps only the active non-model TOML + minimal STEP + two metal ports + headless EM setup/solve/report path.

For Korean documentation, see [README.md](README.md).

## Current Contract
- Version: `0.3.0`
- Active input: [examples/minimal_step_two_port.toml](examples/minimal_step_two_port.toml)
- TOML surface: only `[design]` and `[[non_model_objects]]`
- STEP surface: authored non-model boxes and fixed Tx/Rx port cells
- EM surface: one Tx port, one Rx port, copper pad mesh, radiation boundary, `Setup1`, `Sweep`, and `Output Variables Table1`
- SSW debug inputs [examples/0.3.0_fixed.toml](examples/0.3.0_fixed.toml) and [examples/0.3.0_sweep.toml](examples/0.3.0_sweep.toml) use the same `[constraints]` / `[[constraints.rules]]` surface as 0.2.25 type2, and each enabled SSW coil must satisfy `gcd(turn_n_int, twist_factor) == 1`.
- Default execution is headless, and PyAEDT `False` returns raise immediately.

## Execution
Run tests from `run/`.

```bash
cd run
../.venv/bin/pytest -q ../tests
../.venv/bin/pyright ../src ../entry ../tests
```

Generate the minimal sampled STEP artifacts.

```bash
cd run
../.venv/bin/python ../entry/sample.py
```

Create the headless AEDT setup-ready project.

```bash
cd run
../.venv/bin/python ../entry/build.py
```

Run solve and CSV report export.

```bash
cd run
../.venv/bin/python ../entry/build.py --solve
```

## Artifacts
Default output goes under `run/sampled/minimal/<design_id>/`.

- `sampled.toml`
- `<design_id>.source.toml`
- `<design_id>.repro.toml`
- `<design_id>.dataset.toml`
- `minimal_scene.step`
- `minimal_step_ledger.json`
- `<design_id>.aedt`
- `minimal_imported_ledger.json`
- `Output_Variables_Table1.csv` when `--solve` is used

## Rules
- `python -O` is unsupported because assertions are part of the runtime contract.
- Runtime state under `src/` must not rely on nullable or fallback-driven paths.
- GUI AEDT validation is opt-in only.
- Removed type2, rect-void, and legacy geometry paths are not retained as active or legacy implementation surfaces in 0.3.0.

## Documentation
- Goal: [GOAL.md](GOAL.md)
- Current pipeline: [docs/current-pipeline.md](docs/current-pipeline.md)
- 0.3.0 plan: [sdd/plans/0.3.0-minimal-step-two-port-reset.md](sdd/plans/0.3.0-minimal-step-two-port-reset.md)
- Agent rules: [AGENTS.md](AGENTS.md)

## Compatibility
Long-term backward compatibility is not guaranteed. Minor releases may change spec paths, artifact contracts, and runtime entrypoints.
