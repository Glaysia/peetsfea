---
title: test_type2_single_coil_underlay_boolean_clearance.py
created: 2026-05-04 @ 00:00
updated: 2026-05-06 @ 01:00
tags:
  - tests
  - type2
  - boolean
---

# test_type2_single_coil_underlay_boolean_clearance.py

## Source
- Path: `tests/type2/test_type2_single_coil_underlay_boolean_clearance.py`
- Code note path: `sdd/code/tests/type2/test_type2_single_coil_underlay_boolean_clearance.py.md`
- Status: active

## Single Responsibility
- Focused pure build123d/OCC contract tests for the Type2 single-coil ferrite/PET_PSA priority clearance helper and TX inner void-stack pair span helper.

## Inputs / Outputs
- Inputs: synthetic labeled build123d box solids, optional labeled ferrite group compounds, and synthetic TX inner void-stack descriptors.
- Outputs: assertions on returned ordered scene children, labels, solid counts, volumes, zero FR4/ferrite positive-volume overlap after cutting, and exact TX inner void-stack sheet bounds.

## Canonical State
- Synthetic labels represent ferrite/PET_PSA tools, FR4/PCB blanks, copper pass-through bodies, and optional ferrite group bodies.
- The expected FR4 volume reduction is derived from the synthetic overlap dimensions.
- TX inner void-stack descriptors use a fixed synthetic void span and nominal ferrite/PET_PSA minimum sheet thicknesses.

## Invariants
- Ferrite/PET_PSA tools are preserved and only FR4/PCB blanks are cut.
- Returned top-level labels and order match input top-level labels and order.
- Explicit group selection and predicate-derived tool selection both produce a valid cut.
- Missing tool selection for an expected cut path raises immediately.
- TX inner void-stack generation chooses the largest fitting ferrite/PET_PSA pair count up to four, splits leftover pair span evenly between ferrite and PET/PSA, preserves label order, and fails when one minimum pair cannot fit.

## Fail-Fast Points
- The helper raises when an expected cut has no resolved ferrite/PET_PSA tools.
- The TX inner void-stack builder raises when the void X width is narrower than one minimum ferrite/PET_PSA pair.
- Invalid output geometry would surface through helper assertions before test assertions.

## Collaborators
- [type2_single_coil_underlay.py](../../src/peetsfea/type2_single_coil_underlay.py.md)
- [Type2 Ferrite FR4 Boolean Clearance](../../../plans/0.2.24-type2-ferrite-fr4-boolean-clearance.md)

## Related Tests
- This is the direct helper-level coverage for Slot A of the ferrite/FR4 boolean-clearance plan.

## Change Hazards
- Tests intentionally avoid AEDT and STEP export; integration into scene/export paths must be covered by their owning files.
- Synthetic boxes must keep positive-volume overlap so the boolean cut is observable.
