---
title: type2_tx_plate_stack_array.py
created: 2026-05-04 @ 00:00
updated: 2026-05-04 @ 00:00
tags:
  - type2
  - tx
  - plate-stack
---

# type2_tx_plate_stack_array.py

## Source
- Path: `src/peetsfea/type2_tx_plate_stack_array.py`
- Code note path: `sdd/code/src/peetsfea/type2_tx_plate_stack_array.py.md`
- Status: active implementation boundary for generic TX plate-stack array geometry, even when active export support is limited by current Type2 export policy.

## Single Responsibility
- Build deterministic TX plate-stack array scene shapes and `ModeledObjectSceneData` from a modeled TX plate-stack spec and region owners.
- Preserve branch labels, copied-branch rotation metadata, terminal-edge metadata, and expected body/group contracts for future generic TX plate-stack export support.
- Apply ferrite/PET_PSA/ferrite-family priority clearance to branch PCB/FR4 blanks before STEP export, without AEDT-side subtract.

## Inputs / Outputs
- Inputs are `ModeledTxPlateStackSpec`, `tx_region` owner context, `rx_region_max` owner context, and deterministic seed.
- Outputs are ordered build123d shapes and modeled scene metadata containing body names, groups, canonical coordinates, and terminal metadata.

## Canonical State
- `tx_coil_count`, sampled X/Y/Z usage ratios, owner bounds, branch hinge edges, and copied-branch rotation angles are resolved inside this module.
- `g_ferrite_tx` groups the ferrite-family branch stack members in exported order.
- `g_copper_tx` groups the shared TX plate copper member.
- Each branch owns exactly two PCB/FR4 blanks, `tx_bN_pcb_wall` and `tx_bN_pcb_coil`, and one grouped ferrite-family tool set made from `tx_bN_stack_pet_psa`, `tx_bN_stack_ferrite`, and `tx_bN_stack_air`.

## Invariants / Fail-Fast
- `tx_coil_count < 1`, non-`tx_region` owners, non-YZ owners, non-positive owner sizes, impossible branch thickness, and degenerate copied-branch rotation fail immediately.
- Body labels and expected body/group names must stay deterministic for a fixed spec and seed.
- Ferrite/PET_PSA priority boolean clearance cuts only branch PCB/FR4 blanks and must not mutate ferrite-family member labels or ordering.
- Boolean clearance fails if a branch has no grouped ferrite-family tools, if a cut result is empty, if it produces more than one PCB/FR4 solid, if volume is non-positive, or if the blank label drifts.

## Collaborators
- [type2_plate_stack.py](type2_plate_stack.py.md)
- [type2_step_export.py](type2_step_export.py.md)
- [0.2.24 Type2 Ferrite FR4 Boolean Clearance](../../../plans/0.2.24-type2-ferrite-fr4-boolean-clearance.md)
- [test_type2_tx_plate_stack_array_export.py](../../../code/tests/type2/test_type2_tx_plate_stack_array_export.py.md)
