---
title: type2_step_em_solve.py
created: 2026-04-29 @ 16:50
updated: 2026-04-29 @ 16:50
tags:
  - type2
  - aedt
  - em
---

# type2_step_em_solve.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_em_solve.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_em_solve.py.md`

## Single Responsibility
- Runs the active type2 HFSS analysis setup after setup-ready generation and exports the output-variable report artifact.

## Inputs / Outputs
- Inputs: an `HfssSession`, output directory, setup name, report name.
- Outputs: typed solve result containing setup name and exported report CSV path.

## Canonical State
- `Setup1` is the active analysis setup produced by setup-ready generation.
- `Output Variables Table1` is the active report template owned by the type2 output contract.
- Exported EM artifacts live next to the sampled design AEDT outputs.

## Invariants
- Analysis must raise immediately when AEDT returns `False`.
- The configured report must exist before export.
- The exported CSV path must exist and be a file after export.

## Fail-Fast Points
- Missing report module methods, failed `analyze_setup`, failed `ExportToFile`, missing report name, or missing exported CSV all raise.

## Collaborators
- [protocols.py](../../../aedt/protocols.py.md)
- [type2_step_setup_ready.py](type2_step_setup_ready.py.md)
- [type2_runtime.py](../../../type2_runtime.py.md)

## Related Tests
- [test_type2_step_setup_ready.py](../../../../../tests/backend_em/test_type2_step_setup_ready.py.md)
- [test_build_type2_entry.py](../../../../../tests/type2/test_build_type2_entry.py.md)

## Change Hazards
- PyAEDT API drift around `analyze_setup` or `ReportSetup.ExportToFile` must be reflected in protocols and fakes together.
