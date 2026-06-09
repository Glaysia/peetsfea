---
title: ssw_design_space.py
created: 2026-06-08
updated: 2026-06-08
tags:
  - sdd
  - code
  - ssw
---

# ssw_design_space.py

- Path: `src/peetsfea/ssw_design_space.py`
- Responsibility: parse 0.3.0 SSW sweep-style TOML range surfaces, check candidate inclusion against the reference sweep space, and build short AEDT point identities.
- Inputs: candidate TOML path and reference TOML path, defaulting to `examples/0.3.0_sweep.toml`.
- Outputs: typed design-space check results and `SswAedtIdentity` with `design_id`, `aedt_filename`, `point_hash`, `dimension_count`, and `free_owner_paths`.
- Canonical state: role-qualified free owner paths from the reference sweep and realized candidate point values used in canonical JSON hash payloads.
- Invariants: free paths are reference ranges with `count != 1`, modeled object paths include `role=...`, candidate ranges must be present for every free path, candidate count must be a positive integer, candidate bounds must stay inside reference bounds, and AEDT identity generation requires every free path to be a single realized value.
- Fail-fast points: invalid TOML structure, malformed range arrays, duplicate modeled object roles, missing free paths, integer flag mismatch, out-of-reference bounds, non-positive counts, or non-point identity requests.
- Collaborators: [debug_view_0_3_0_ssw.py](../../../entry/debug_view_0_3_0_ssw.py.md), [ssw_ports.py](backend/pyaedt/ssw_ports.py.md).
- Tests: [test_ssw_design_space.py](../../../tests/test_ssw_design_space.py.md).
- Hazards: do not include seed, TOML comments, TOML ordering, grid index, or candidate count in the point hash; do not let the identity stem affect AEDT imported object/body names.
- Related plan: [0.3.0 ssw aedt design space identity](../../../plans/0.3.0-ssw-aedt-design-space-identity.md).
