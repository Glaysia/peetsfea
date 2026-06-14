---
title: ssw_random_sample_reports.py
created: 2026-06-14
updated: 2026-06-14
tags:
  - sdd
  - code
  - ssw
---

# ssw_random_sample_reports.py

- Path: `src/peetsfea/ssw_random_sample_reports.py`
- Responsibility: provide function-first orchestration for sampling one strict-subset SSW fixed TOML, exporting AEDT port artifacts, solving HFSS, exporting the three SSW report CSVs, and preserving the sampled design-space point.
- Inputs: candidate TOML path or serialized TOML text, output directory, seed, run mode, reference TOML path, and optional HFSS factory for tests.
- Outputs: typed API result with mode, seed, dimension count, free owner paths, full `point_values`, design identity, sampled TOML path, point ledger path, AEDT path, CSV paths, CSV text keyed by report name, setup pass counts, and solve telemetry.
- Canonical state: `sample_point_ledger.json` and the sampled fixed TOML are the replayable point record; `point_hash` is only a deterministic fingerprint derived from `free_owner_paths` and `point_values`.
- Invariants: candidate sampling uses the existing strict subset design-space policy, exactly one sample is generated, all free owner paths must appear in `point_values`, CSV keys are exactly `Results1_Pass`, `Results2_Last`, and `Results3_Freq`, `semi_dry` uses setup pass counts 5/1/1, solve telemetry from the backend is copied into the result ledger, and serialized TOML input is first materialized as `input.toml`.
- Fail-fast points: invalid mode, invalid candidate design space, exhausted sample attempts, missing point values, hash mismatch through identity generation, failed artifact export, failed AEDT solve/export, missing CSV files, or failed ledger write.
- Collaborators: [ssw_design_space.py](ssw_design_space.py.md), [ssw_ports.py](backend/pyaedt/ssw_ports.py.md), [debug_view_0_3_0_ssw.py](../../../entry/debug_view_0_3_0_ssw.py.md).
- Tests: [test_ssw_design_space.py](../../../tests/test_ssw_design_space.py.md), [test_ssw_ports.py](../../../tests/backend_em/test_ssw_ports.py.md).
- Change hazards: do not infer point coordinates from `point_hash`, do not add fallback solve settings beyond the explicit `semi_dry` 5/1/1 policy, and do not silently return partial CSV output.
