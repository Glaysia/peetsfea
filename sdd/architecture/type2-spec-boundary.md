---
title: Type2 Spec Boundary
created: 2026-05-03 @ 00:00
updated: 2026-05-03 @ 00:00
tags:
  - spec
  - sdd
---

# Type2 Spec Boundary

이 문서는 active type2 TOML/spec boundary의 graph owner다.
역할은 입력 TOML을 fail-fast로 읽고, generated TOML을 재현 가능하게 쓰며, EM output variable 계약을 parser level에서 고정하는 것이다.

## Owned Surface
- TOML load and minimal shape validation: [loader.py](../code/src/peetsfea/spec/loader.py.md)
- TOML rendering for generated active artifacts: [toml_render.py](../code/src/peetsfea/spec/toml_render.py.md)
- EM output/report variable parsing: [outputs.py](../code/src/peetsfea/spec/outputs.py.md)

## Direct Verification
- Lightweight public spec/tool import and sampled TOML rendering: [test_type2_spec_tools.py](../code/tests/type2/test_type2_spec_tools.py.md)
- Public `type2_step_spec` facade import surface: [test_type2_step_spec_import_surface.py](../code/tests/type2/test_type2_step_spec_import_surface.py.md)

## Exceptional Links
- EM report variable names are intentionally owned by [type2-em-report-contract](type2-em-report-contract.md), while parser enforcement lives here.
- Runtime STEP import consumes retained `outputs` through [type2-step-import-boundary](type2-step-import-boundary.md).
- Setup-ready report generation consumes validated outputs through [type2-em-setup-boundary](type2-em-setup-boundary.md).

## Invariants
- Required TOML shape failures are hard failures, not fallback paths.
- Generated TOML must preserve deterministic owner/value materialization.
- Output mode and variable parsing must reject unsupported names, expressions, and modes before AEDT runtime work begins.
