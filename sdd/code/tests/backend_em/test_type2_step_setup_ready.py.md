---
title: test_type2_step_setup_ready.py
created: 2026-04-18 @ 09:09
updated: 2026-05-13 @ 00:00
tags:
  - test
  - em
---

# test_type2_step_setup_ready.py

## Source
- Path: `tests/backend_em/test_type2_step_setup_ready.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_step_setup_ready.py.md`
- Status: active
- Primary graph owner: [type2-em-setup-boundary](../../../architecture/type2-em-setup-boundary.md)

## 역할
- setup-ready runtime의 import, mesh, boundary, RX port, RX report assembly behavior를 검증한다.
- 0.2.24 SDD 기준 `RxOnly` and `TxRx` behavior are active documented targets.
- solve-enabled setup tests verify analysis and report CSV export before desktop release.
- `tx_outer_single_coil` 포함 조합은 setup-ready 전에 fail-fast rejection 되는지 검증한다.
- Tx 양극/음극 브릿지 멤버(`tx_pos_bridge_pcb/copper`, `tx_neg_bridge_pcb/copper`)는 modeled 대상이 아닌 `non_model` 타겟으로만 남는지를
  회귀로 검증한다.
- `assign_type2_lumped_ports`에서 단일 코일 터미널 메타데이터의 `vertices_xyz`와
  `single_coil_port_v1` sheet contract를 AEDT world 좌표 그대로 사용해 경계 엣지를 선택하는 경로를 검증한다.
- Setup-ready fake ledgers include v3 exported-body coordinates so imported body bbox validation is exercised before setup operations.

## Canonical state
- Tests should verify RX conductor mesh and one RX lumped port.
- Tests should verify RxOnly does not create TX ports or TX output variables.
- Tests should verify TxRx keeps TX inner + RX ledger entries, creates TX/RX port assignments, assembles two-terminal report variables, and meshes TX inner + RX conductors.
- Mesh tests verify `Length1.MaxLength` is derived from canonical TX/RX trace widths rather than a fixed global value.
- TxRx setup fixtures keep `tx_inner_single_coil` owned by `tx_inner_region`, matching the lower-X wall-side anchoring contract enforced during import styling.
- Active `tx_inner_single_coil` setup fixtures use the current fixed/sweep exported names `tx_inner_pcb_l0` and `tx_inner_copper_l0`; multilayer copper-stack naming is reserved for explicit synthetic stack tests outside the active TX-inner fixture path.
- TxRx setup fixtures include the `tx_inner_actual_region` non-model member and imported STEP name whenever
  `tx_inner_single_coil` participates, so setup-ready fake import ledgers satisfy strict actual-region validation before AEDT setup operations run.
- TX inner passive body fixtures keep `canonical_coordinates` semantic and use `exported_body_canonical_coordinates` for imported body union bounds.
- 포트 할당 단위 테스트에 `tx_inner_single_coil` paired mode (`tx_inner_single_coil` + `rx_single_coil`)를 추가로 검증한다.
- The active full setup-ready happy path uses a single `rx_single_coil` modeled entry.
- TxRx full setup-ready happy path uses `tx_inner_single_coil` and `rx_single_coil`; a passive
  `tv_aluminum_plate` may also be imported and styled while staying out of mesh, ports, sources, and reports.
- Active fixed/sweep setup-ready fixtures treat TX inner as layer-count one and must not expect `tx_inner_copper_stack`.
- `non_model` 장면에서의 양극/음극 브릿지 멤버는 modeled coil/port payload에 포함되지 않고 `non_model_objects[*].imported_object_names`에 유지되어야 한다.
- 단일 코일 TX 포트 할당 테스트는 `terminal_metadata.vertices_xyz` 기반 엣지 좌표가
  `oboundary.AssignLumpedPort(..., Edges:=...)` 단계에서 그대로 반영되는지를 확인한다.
- TxRx test ledgers carry schema/hash fields, so setup-ready tests exercise the same stale-artifact guard as import tests.
- TX inner actual-underlay bodies may be present in imported object names, but setup-ready assertions keep ports, sources, reports, and mesh based on TX/RX conductors only.
- EM input construction keeps `tx_underlay_pet_psa_u*` and `tx_underlay_ferrite_u*` out of conductor and ferrite-ready object lists for the setup-ready contract.
- TX inner void-stack bodies `tx_void_pet_psa_u*` and `tx_void_ferrite_u*` are passive import names and must stay out of conductor, mesh, port, source, and report targets.
- Disabling `void_stack_present` removes only `tx_void_*` members; bottom `tx_underlay_*` members remain passive setup-ready inputs when underlay repeat count is positive.
- Disabled void-stack setup-ready regression coverage keeps `g_ferrite_tx` underlay-only membership and verifies conductor, mesh, port, source, output-variable, and report targets are unchanged from the enabled passive-body contract.
- Future two-terminal report names are documented in `sdd/architecture/type2-em-report-contract.md` but are not active RxOnly assertions.
- Solve/export tests use the same active output-variable report created by setup-ready generation.
- Attached-HFSS setup tests cover the explicit flag that skips AEDT `ValidateDesign()` while still saving and detaching.
- Mesh setup assertions expect `Length1` with `RestrictElem=True`, `NumMaxElem=24000`, `RestrictLength=True`, and trace-width-derived `MaxLength`.

## Invariants / fail-fast
- PyAEDT false-return handling remains fail-fast.
- Missing RX/TX terminal metadata or unsupported role pairings must fail with context.
- Malformed single-coil runtime port sheet metadata fails on `vertices_xyz`; plate-stack tests keep the legacy `port_sheet_vertices_xyz` contract isolated to plate-stack roles.
- TX inner setup fixtures must include the non-modeled `tx_inner_region` owner before import-bound validation runs.
- TX inner setup fixtures must include `tx_inner_actual_region` provenance and imported names for positive and downstream
  AEDT-region failure cases; tests that intentionally omit the owner assert the earlier ledger-validation failure.
- Skipping AEDT `ValidateDesign()` must be opt-in only and must not affect default fail-fast validation tests.
- Passive TX inner actual-underlay names must not become mesh targets or port/source/report participants.
- Passive TX inner void-stack names must not become mesh targets or port/source/report participants, and extra void pairs such as `tx_void_ferrite_u1` / `tx_void_pet_psa_u1` must not appear in active fixed-example setup fixtures.
- Passive `tv_aluminum_plate` must stay a modeled aluminum object without becoming a mesh target or port/source/report participant.
- Any `tx_outer_single_coil` source ledger fixture must fail before HFSS setup operations.
- Missing or invalid `canonical_coordinates.trace_width_mm` must fail before PyAEDT mesh assignment.

## Graph links
- Primary owner: [type2-em-setup-boundary](../../../architecture/type2-em-setup-boundary.md)
- Direct verification: [type2_step_setup_ready.py](../../src/peetsfea/backend/pyaedt/type2_step_setup_ready.py.md)
- Exceptional contract: [type2-em-report-contract](../../../architecture/type2-em-report-contract.md)
- Related plan: [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
- Related plan: [0.2.24 Type2 Trace Width Mesh Length](../../../plans/0.2.24-type2-trace-width-mesh-length.md)
- Related plan: [0.2.25 Type2 Port Sheet Contract Rewrite](../../../plans/0.2.25-type2-port-sheet-contract-rewrite.md)
- Related plan: [0.2.25 Type2 Exported Body Bounds Import Validation](../../../plans/0.2.25-type2-exported-body-bounds-import-validation.md)
