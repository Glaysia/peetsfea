---
title: ssw_design_space.py
created: 2026-06-08
updated: 2026-06-10
tags:
  - sdd
  - code
  - ssw
---

# ssw_design_space.py

- Path: `src/peetsfea/ssw_design_space.py`
- Responsibility: parse 0.3.0 SSW sweep-style TOML range surfaces, check candidate inclusion against the reference sweep space, build short AEDT point identities, and sample deterministic fixed TOML points with explicit realized point values.
- Inputs: candidate/sweep TOML path, output directory for sampled TOMLs, sample count, seed, maximum attempts per sample, and reference TOML path defaulting to `examples/0.3.0_sweep.toml`.
- Outputs: typed design-space check results, `SswAedtIdentity`, sampled TOML batch metadata, generated paths, point identities, and full free-owner `point_values` for each sampled point.
- Canonical state: role-qualified free owner paths from the reference sweep, realized candidate point values used in canonical JSON hash payloads, explicit sampled `point_values`, and sampled fixed TOML files named by point identity.
- Invariants: free paths are reference ranges with `count != 1`, modeled object paths include `role=...`, candidate ranges must be present for every free path, candidate count must be a positive integer, candidate bounds must stay inside reference bounds, non-reference varying ranges are rejected for sampling, and AEDT identity generation requires every free path to be a single realized value.
- Fail-fast points: invalid TOML structure, malformed range arrays, duplicate modeled object roles, missing free paths, integer flag mismatch, out-of-reference bounds, non-positive counts, non-point identity requests, pre-existing output files, duplicate sampled identities, or exhausted sample attempts.
- Collaborators: [debug_view_0_3_0_ssw.py](../../../entry/debug_view_0_3_0_ssw.py.md), [ssw_ports.py](backend/pyaedt/ssw_ports.py.md), [ssw_step.py](ssw_step.py.md).
- Tests: [test_ssw_design_space.py](../../../tests/test_ssw_design_space.py.md).
- Hazards: do not include seed, TOML comments, TOML ordering, grid index, or candidate count in the point hash; do not treat the hash as reversible point storage; do not let the identity stem affect AEDT imported object/body names; keep sampling deterministic without mutating the source sweep TOML.
- Related plans: [0.3.0 ssw aedt design space identity](../../../plans/0.3.0-ssw-aedt-design-space-identity.md), [0.3.0 ssw fixed toml sampling](../../../plans/0.3.0-ssw-fixed-toml-sampling.md).
