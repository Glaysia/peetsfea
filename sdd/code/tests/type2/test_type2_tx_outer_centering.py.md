---
title: test_type2_tx_outer_centering.py
created: 2026-05-03 @ 14:30
updated: 2026-05-04 @ 00:00
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
- Verifies that `tx_outer_single_coil` placement remains anchored in the `tx_outer_region_prism` local frame after the outer-region tilt is resolved.
- Verifies that TX outer `x_position_ratio` is applied to the design outer footprint center interval in the prism-local virtual owner before tilt, with no post-rotation world-X shift.
- Verifies that TX outer passive void-stack bodies, when present, are transformed through the same prism-local outer placement path for X/Y and extend to the base `tx_region.max_z` world plane.
- Verifies that TX outer bottom-underlay bodies, when present, use the outer design/actual footprint and the same prism-local outer placement path.
- Verifies raw overshoot metadata when the pure scene contract exposes it.
- Keeps regression coverage in the pure-Python scene path by validating resolved scene coordinates without invoking STEP export or AEDT.

## Inputs / Outputs
- Inputs are the realistic type2 fixture spec (`examples/type2_fixed.toml`) resolved through non-model and modeled scene paths using deterministic seed `17`.
- Outputs are pass/fail assertions over:
  - `build_modeled_single_coil_scene_data`,
  - `resolve_non_model_scene_specs`,
  - `resolve_tx_outer_single_coil_fit_envelope`,
  - `require_tx_outer_region_prism_provenance`,
  - `resolve_tx_outer_region_tilt_frame`.

## Canonical State
- `tx_outer_region` is resolved from `examples/type2_fixed.toml` through the non-model resolver, which records `tx_outer_region_prism` provenance.
- `tx_outer_single_coil` is resolved from the same fixture and is placed against the resolved `tx_outer_region` owner.
- Prism-local frame state comes from `require_tx_outer_region_prism_provenance("tx_outer_region")` and `resolve_tx_outer_region_tilt_frame`.
- Expected bounds are derived from the resolved prism top edge, semantic Y span, owner height, and base `tx_region.max_z` world plane rather than fixed example coordinates.

## Invariants
- The design outer footprint center must satisfy `target_center_x = design_outer_half_x + (owner_x_span - design_outer_x_span) * x_position_ratio`.
- At ratio `0.0`, the design outer X minimum must touch the prism-local owner minimum; at ratio `1.0`, the design outer X maximum must touch the owner maximum.
- The local fit envelope and final modeled body vertices must remain inside the prism-local X/Y span, with the main outer body Z staying between the resolved owner bottom side and the prism top plane.
- The modeled canonical AABB must match the world AABB produced by transforming prism-local fit-envelope bounds through the tilt frame, with no additional world-X post-centering shift.
- Projected final shape vertices must remain inside the prism-local X/Y spans and must not rise above the prism top plane.
- Projected outer void-stack vertices must remain inside the realized outer void X/Y window, must reach `tx_region.max_z` in world Z, and must expose a world-horizontal top clip face on that plane.
- Projected outer bottom-underlay vertices must match the outer design/actual X/Y footprint and sit below the outer body in prism-local `-Z`.
- If raw outer void-stack overshoot metadata is exposed by scene data, it must equal one fixed PET/PSA plus ferrite pair before top clipping.
- The test remains non-AEDT and fails fast if any resolved geometry contract breaks.

## Fail-Fast Points
- `resolve_tx_outer_single_coil_fit_envelope` raises if outer-region tilt provenance is unavailable or malformed.
- `resolve_non_model_scene_specs` raises if TX-derived regions resolve to unsupported or ambiguous topology.
- `require_tx_outer_region_prism_provenance` raises if the resolved outer prism provenance has not been registered.

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
- If `tx_outer_single_coil` is rotated into the prism frame and then shifted by world-X AABB centering, this test fails because final modeled bounds no longer match the pure prism-local transform.
- If the prism provenance keys or tilt-frame semantics change, update these tests with the new canonical prism-local frame contract rather than fixed fixture coordinates.
