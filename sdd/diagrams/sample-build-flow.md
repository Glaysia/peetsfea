---
title: Sample Build Flow
created: 2026-04-17 @ 09:09
updated: 2026-06-01 @ 00:00
tags:
  - diagram
  - minimal
---

# Sample Build Flow

```mermaid
flowchart TD
    Source["minimal source TOML"]
    Sample["entry/sample.py"]
    Snapshots["sampled/source/repro/dataset TOML"]
    Step["minimal_scene.step + minimal_step_ledger.json"]
    Build["entry/build.py"]
    Hfss["minimal_em.py headless HFSS setup"]
    Solve["optional --solve CSV report"]

    Source --> Sample
    Sample --> Snapshots
    Sample --> Step
    Step --> Build
    Build --> Hfss
    Hfss --> Solve
```

## Notes
- The generated STEP contains authored non-model boxes plus fixed Tx/Rx port cells.
- Mesh, ports, sources, setup, sweep, and report creation are owned by [minimal_em.py](../code/src/peetsfea/backend/pyaedt/minimal_em.py.md).
- Old geometry generation branches are outside the 0.3.0 graph.
