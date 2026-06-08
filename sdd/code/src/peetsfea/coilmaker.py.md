---
title: coilmaker.py
created: 2026-06-07
updated: 2026-06-07
tags:
  - sdd
  - code
---

# coilmaker.py

- Path: `src/peetsfea/coilmaker.py`
- Responsibility: generate the CadQuery SSW/normal coil assembly and transformer-ready action trace from validated coil dimensions and coil parameters.
- Inputs: `RuntimeConfig` with fixed dimensions, common coil parameters, spiral parameters, and SSW parameters.
- Outputs: CadQuery assembly children for FR4 boards and copper, plus materialized action tokens that can be serialized as TOML by callers.
- Canonical state: dataclass parameter values, derived frame dimensions, normal/spiral terminal trace axis and perpendicular landing direction, action token refs, and generated CadQuery child names.
- Invariants: SSW generation is trace-first, normal/spiral port landing pad size follows the realized trace width, normal/spiral landing uses the pad edge perpendicular to the outer-terminal trace segment's cardinal direction, action token payloads stay scalar/tuple/ref based, generated copper is one intended conductor, and generated assemblies are deterministic for the same config.
- Fail-fast points: invalid dimensions, collapsed trace geometry, unsupported SSW trace construction, non-transformer-ready token payloads, empty rendered parts, and failed export-oriented generation.
- Collaborators: [ssw_step.py](ssw_step.py.md).
- Tests: [test_ssw_step.py](../../../tests/test_ssw_step.py.md).
- Change hazards: do not reintroduce normal-coil fallback or minimal two-port placeholder behavior for the 0.3.0 SSW path, do not make normal/spiral port pad size diverge from trace width, and do not replace the terminal-trace-axis landing direction with frame-axis heuristics.
- Related plan: [0.3.0 ssw fixed ocp viewer](../../../plans/0.3.0-ssw-fixed-ocp-viewer.md).
