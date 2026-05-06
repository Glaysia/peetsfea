---
title: test_type2_tx_outer_centering.py
created: 2026-05-03 @ 14:30
updated: 2026-05-06 @ 00:00
tags:
  - test
  - type2
  - placement
---

# test_type2_tx_outer_centering.py

## Source
- Path: `tests/type2/test_type2_tx_outer_centering.py`
- Code note path: `sdd/code/tests/type2/test_type2_tx_outer_centering.py.md`
- Status: active

## Single Responsibility
- Verifies the active Type2 STEP export no longer emits `tx_outer_single_coil` modeled ledgers, `tx_outer_actual_region`, outer passive body labels, outer ferrite groups, or inner/outer bridge members.
- Keeps regression coverage focused on the active export contract while preserving dormant TX outer helper code outside the active generation path.

## Inputs / Outputs
- Inputs are the realistic type2 fixture spec (`examples/type2_fixed.toml`) exported with deterministic seed `17`.
- Outputs are pass/fail assertions over the resulting active ledger and STEP scene labels.

## Canonical State
- `tx_inner_rect_void_coil` and `rx_rect_void_coil` remain the active modeled ledger entries.
- `tx_outer_region` may remain as guide/provenance context.
- `tx_outer_actual_region`, `tx_outer_rect_void_coil`, outer passive body labels, `g_ferrite_tx_outer`, and bridge members are forbidden.

## Invariants
- Active export must not produce any modeled object with role `tx_outer_single_coil`.
- Active export must not produce any non-modeled member or STEP label for the removed outer actual region or bridge solids.
- Active export must keep `tx_inner_single_coil` and `rx_single_coil` modeled entries.

## Fail-Fast Points
- Export fails if removed TX outer artifacts are still present in ledger or scene labels.

## Collaborators
- [type2_single_coil_scene.py](../../src/peetsfea/type2_single_coil_scene.py.md)
- [type2_non_model_scene.py](../../src/peetsfea/type2_non_model_scene.py.md)
- [tx_rect_void.py](../../src/peetsfea/tx_rect_void.py.md)
- [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)

## Related Tests
- [test_generate_type2_step.py](test_generate_type2_step.py.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- [0.2.24 Type2 TX Outer Void Stack TX Region Extension](../../../plans/0.2.24-type2-tx-outer-void-stack-tx-region-extension.md)

## Change Hazards
- If loader/spec workers complete removal, these tests continue to assert active absence.
- If dormant TX outer helper code remains, this test must not reactivate it through the export path.
