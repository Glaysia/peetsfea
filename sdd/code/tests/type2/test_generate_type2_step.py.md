---
title: test_generate_type2_step.py
created: 2026-04-19 @ 17:35
updated: 2026-04-22 @ 04:35
tags:
  - tests
  - type2
  - export
---

# test_generate_type2_step.py

## Source
- Path: `tests/type2/test_generate_type2_step.py`
- Code note path: `sdd/code/tests/type2/test_generate_type2_step.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-plate-stack-equivalent-3-slab]], [[sdd/plans/0.2.22-type2-plate-stack-z-usage-ratio]], [[sdd/plans/0.2.22-type2-plate-stack-y-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-plate-stack-parallel-array]], [[sdd/plans/0.2.22-type2-single-coil-void-usage-ratio]], [[sdd/plans/0.2.22-type2-tx-actual-region-pcb-non-model]], [[sdd/plans/0.2.22-type2-tx-rect-void-columns-geometry]]
- Direct verification target: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- type2 parser/export/ledger contract regression을 검증한다.

## Canonical coverage
- `tx_plate_stack`, `rx_plate_stack`, and `rx_single_coil` parser/export acceptance
- active fixed example loader expects the full 0.2.21-style output-variable list and the active TX/RX modeled pair.
- active fixed example also expects derived non-model `tx_region_actual` with fixed 0.3 X/Y usage ratios and 1x1 division.
- export ledger coverage verifies `tx_region_actual` is min-X anchored, Y-centered, full-Z relative to `tx_region`, and can resolve to 3x3 concrete tiles.
- export ledger coverage verifies `tx_region_actual_stack_space` bodies are generated one-for-one with concrete `tx_region_actual` tiles, with fixed `total_thickness_mm = 5.0`, top-face alignment before tilt, and scale-derived similar footprint.
- export coverage verifies `tilt_enabled = 1` rotates only the stack-space bodies toward the modeled RX center, keeps guide tiles axis-aligned, and clamps tilted stack-space bounding boxes under owning tile tops.
- `tx_rect_void_columns` generation/export behavior is now validated as STEP handoff success for full STEP export:
  - series specs export one fused `tx_rect_void_columns_copper` body, per-tile PCBs, ordered series link metadata, and exactly two future tab faces,
  - parallel specs export one fused `tx_rect_void_columns_copper` body, per-tile PCBs, balanced collector pour bus/patch metadata, and exactly two future tab faces,
  - parser-bypass simulations (mocked loader + preflight no-op) still execute through full export and keep the same success contract,
  - generated specs using `tx_rect_void_columns` with varied tiling/turn matrices produce expected body metadata counts and scene bodies.
  - TX columns export helpers assert final `tx_rect_void_columns_copper` has zero positive-volume intersection with every
    exported `txrvc_*_pcb_l*` body.
  - grid contract regression explicitly covers `1x1`, `2x3`, `3x3` and validates `txrvc_x*_y*_pcb_l*`, series `txrvc_x*_y*_cu_l*`, series `txrvc_x*_y*_stub_*`, and parallel fused-copper naming/body-count 계약.
  - tilted series export verifies every generated `txrvc_x*_y*_stub_*` terminal body shares the same bottom Z, using the lowest natural stub as the common floorward height.
  - safe-turn grid variant fixtures keep TOML truth ranges for allocation surface, including canonical `equivalent_turn_count = [false, 0.1111111111111111, 31.0, 100]` and `turn_weight_c = [false, -0.3, 0.3, 21]`.
  - fixed-weight symmetry diagnostics now cover `1x3` and `2x3` layouts: Y-mirrored tiles at equal RX distance must realize equal per-tile turn counts and the body naming/count contract remains valid.
- `export_type2_tx_single_coil_artifact` continues to reject `tx_rect_void_columns` role at dispatch.
- `tx_rect_void_columns` parser contract coverage validates parser-only acceptance and exact schema ranges for:
  - `layer_count`, `layer_gap_mm`, `terminal_stub_length_mm`,
  - `connection_mode`, `equivalent_turn_count`,
  - `turn_weight_a/b/c`.
- canonical `equivalent_turn_count` sweep coverage uses `[false, 0.1111111111111111, 31.0, 100]`, while fixed single-candidate values within `[0.1111111111111111, 31.0]` remain valid.
- `tx_rect_void_columns` parser contract rejects legacy keys `turn_count_x0/x1/x2`, `parallel_equivalent_turn_count`, `column_connection_mode`, `row_connection_mode`, `series_total_turn_count`, and `parallel_total_turn_count`.
- RX single-coil public schema uses `outer_x_usage_ratio` / `outer_y_usage_ratio`; parser resolves owner-span-scaled `outer_x_mm` / `outer_y_mm` for core delegation.
- single-coil public schema uses `void_usage_ratio` for centered equal X/Y void size; legacy type2 single-coil `outer_*_mm` and split/centered `void_*` public keys are unsupported.
- `examples/type2_sweep.toml` is the mutable sampling SSOT and this test file must not pin its concrete sweep values.
- object id mismatch / coil-only field rejection
- plate-stack `turn_count`, `metal_fill_factor`, `z_usage_ratio`, `y_usage_ratio` validation plus explicit rejection of removed `shoe_depth_mm`
- TX `tx_coil_count` and `tx_array_x_usage_ratio` v4 parser validation is covered either here or in the dedicated count/sampling regression.
- TX/RX pre-unite baseline contract keeps per-turn/bridge/stub segment bodies; final handoff contract은
  role-level copper/ferrite role bodies로 정규화되며 6-body exact-name 순서를 유지한다.
- TX top-anchored `z_usage_ratio` Z window over global `Y=0` centered `y_usage_ratio` Y window + `min_x` anchor
- RX bottom-anchored `z_usage_ratio` Z window over global `Y=0` centered `y_usage_ratio` Y window + `min_x` anchor
- reduced-height plate-stack conductor/PCB/ferrite placement without shoe cutout bands
- plate-stack striped copper Z 배치는 pitch-slot centered placement를 검증한다.
- wall-side `N`, coil-side `N-1`, bridge `2N-2`, stub 2개 contract
- role별 단일 ferrite/copper group contract:
  - `g_copper_tx -> [tx_plate_copper]`, `g_ferrite_tx -> [tx_stack_pet_psa, tx_stack_ferrite, tx_stack_air]`
  - `g_copper_rx -> [rx_plate_copper]`, `g_ferrite_rx -> [rx_stack_pet_psa, rx_stack_ferrite, rx_stack_air]`
- plate-stack role에서 `g_copper_*` 또는 `g_ferrite_*` 누락/멤버 mismatch를 회귀 테스트로 반드시 잡는다.
- TX array export coverage must keep `N=1` compatibility and verify `N>1` branch-local names with one `tx_plate_copper`.
- merged material ferrite-member ordering (`stack_pet_psa -> stack_ferrite -> stack_air`)
- plate-stack merged material body는 export-side unite 완료 후 label당 exactly one solid(`Solid`)로 유지
- plate-stack ferrite group member는 merged exact names 3개만 포함하고 그룹 순서는
  `stack_pet_psa -> stack_ferrite -> stack_air`를 유지
- plate-stack ferrite group object(`g_ferrite_tx`, `g_ferrite_rx`)의 child label order가 exact member order와 일치해야 한다.
- plate-stack export scene/ledger에 `*_stack_*_uN`/`SOLID*` label이 나타나면 contract 위반으로 간주한다.
- equivalent ferrite-family geometry는 X 순서와 두께를 직접 검증한다:
  `pcb_wall.max_x -> PET/PSA(1.5) -> ferrite(2.0) -> air(0.2) -> pcb_coil.min_x`.
- pre-unite 라벨(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`)이 exported/imported handoff body list에
  남아 있으면 즉시 실패로 본다.
- single-coil ferrite families(`tx_wall_*`, `under_rx_*`) export 시 동일 ferrite-group contract
- RX single-coil full backing verifies `under_rx_*` three-slab full-fill thickness, non-overlap with RX coil bodies, and physical `-X -> +X` order `air -> PET/PSA -> ferrite -> rx_pcb/rx_copper`.
- active mixed default must export TX plate-stack bodies and RX `rx_pcb_l0` / `rx_copper_l0` bodies together.
- plate-stack `stub_port` terminal metadata + metadata-only reconstructed sheet geometry
- plate-stack terminal stubs and sheet metadata use `active_y_min - 5.0 mm` for the left-side `-Y` endpoint.
- `terminal_metadata.input_stub_body_name`/`output_stub_body_name`은 pre-unite 라벨(`*_stub_in/out`)을 참조해야 하며
  imported final copper body명을 가리키면 안 된다.
- bridge contract regression:
  - bridge bbox X span은 full thickness가 아니라 interior span(`wall copper inner face -> coil copper inner face`)이어야 한다.
  - `tx_bridge_s*` / `rx_bridge_s*`는 wall/coil copper turns 및 notched slab bodies(`pcb_wall`, `pcb_coil`, `stack_pet_psa`, `stack_ferrite`, `stack_air`)와 positive-volume intersection이 없어야 한다.
  - same-edge neighboring bridges (`Y=max`끼리, `Y=min`끼리)도 positive-volume intersection이 없어야 한다.

## 변경 시 주의점
- fixed example role drift와 mixed-pair exact-name order drift를 같은 테스트 층에서 잡아야 한다.
- sweep example TOML 값 변경은 authoring change로 취급하며, parser/export unit tests가 구체 range 값을 검사하지 않는다.
- `tx_region_actual` fixture updates must keep backend non-model import fixture member names in sync, including multi-tile names and `tx_region_actual_stack_space_*` companions.
- exact name/order drift 검사는 pre-unite segment contracts와 final export-contract를 함께 검증해야 한다. RX and single-branch TX stay at `6`; TX arrays expand branch-local non-copper names.
- `tx_rect_void_columns` 성능 점검은 default pytest에 포함하지 않고 수동으로만 운영한다.
  - 권장 수동 명령: `cd run && ../.venv/bin/python -m pytest ../tests/type2/test_generate_type2_step.py -k "tx_rect_void_columns_grid_variants" --durations=10 -q`
