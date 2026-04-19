---
title: type2_plate_stack.py
created: 2026-04-19 @ 21:42
updated: 2026-04-19 @ 15:55
tags:
  - step-export
  - tx
  - rx
  - plate-stack
---

# type2_plate_stack.py

## Source
- Path: `src/peetsfea/type2_plate_stack.py`
- Code note path: `sdd/code/src/peetsfea/type2_plate_stack.py.md`
- Status: active

## Ownership
- Primary plan: [[sdd/plans/0.2.22-type2-plate-stack-copper-unite-grouping]]
- Current topology plan: [[sdd/plans/0.2.22-type2-plate-stack-equal-stripes]]
- Primary architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]

## 역할
- active TX/RX plate-stack geometry contract의 canonical owner다.
- role config 차이만으로 TX `tx_plate_stack`와 RX `rx_plate_stack` scene data를 모두 만든다.

## 입력 / 출력
- 입력: plate-stack modeled spec, placement owner spec
- 출력: pre-unite segment bodies(내부 라벨), final handoff용 병합 상태, explicit copper/ferrite groups, canonical coordinates, `stub_port` terminal metadata를 포함한 modeled scene data

## Canonical state
- TX는 `tx_region` full `YZ`, `min_x` anchor, `+X` stack를 사용한다.
- RX는 `rx_region_max` full `YZ`, `min_x` anchor, `+X` stack를 사용한다.
- wall-side copper stripe count와 coil-side copper stripe count는 모두 `N = turn_count`이다.
- active conductor 높이는 full owner `Z` span이다.
- pre-unite exact flat body order는 다음이며 최종 handoff의 exported body가 아니다:
  `*_copper_wall_t*`, `*_pcb_wall`, merged `*_stack_pet_psa`,
  merged `*_stack_ferrite`, merged `*_stack_air`, `*_pcb_coil`,
  `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`.
- 최종 handoff는 역할별로 하나의 united copper 본체를 가진다:
  TX `tx_plate_copper`, RX `rx_plate_copper`.
- 이 최종 본체는 STEP export, import reconstruction, mesh payload에 그대로 사용되는 role-level conductor이다.
- 역할별 final exported body count는 정확히 `6`:
  `*_plate_copper`, `*_pcb_wall`, `*_stack_pet_psa`, `*_stack_ferrite`, `*_stack_air`, `*_pcb_coil`.
- bridge body의 X span은 wall copper와 coil copper 사이 interior-only 구간이다.
- wall/coil striped copper는 각 pitch slot의 lower-bound 정렬이 아니라 centered 정렬이다.
  - `pitch_z = owner_size_z / (turn_count + 0.5)`
  - `trace_height_z = pitch_z * metal_fill_factor`
  - `stripe_center_offset_z = (pitch_z - trace_height_z) / 2`
  - wall start: `z_min + i * pitch_z + stripe_center_offset_z`
  - coil start: `z_min + pitch_z/2 + i * pitch_z + stripe_center_offset_z`
- bridge sequence는 `wall0 -> coil0 -> wall1 -> ... -> wallN-1 -> coilN-1`이며
  bridge count는 `2 * N - 1`이다.
- `*_pcb_wall`, merged `*_stack_*`, `*_pcb_coil`은 bridge가 지나는 edge strip + Z window를 notch로 비워 bridge와 positive-volume overlap이 없다.
- bridge `z` window는 owner `Z` bounds clip 이후 same-edge 누적 max clip을 적용해
  같은 edge의 neighboring bridge끼리 positive-volume overlap을 만들지 않는다.
- merged `*_stack_*` body는 ferrite-family set member를 deterministic connector lane으로 export-side에서 단일 연속 solid로 묶는다.
- connector lane은 bridge clearance/notch 규칙을 깨지 않도록 bridge가 없는 deterministic Z band를 사용한다.
- ferrite family는 role당 정확히 1개 explicit group만 export한다:
  TX `g_ferrite_tx`, RX `g_ferrite_rx`.
- ferrite group member order는 merged 3-body exact-name contract다:
  `*_stack_pet_psa -> *_stack_ferrite -> *_stack_air`.
- copper family도 role당 정확히 1개 explicit group만 export한다:
  TX `g_copper_tx -> [tx_plate_copper]`, RX `g_copper_rx -> [rx_plate_copper]`.
- 각 merged stack body는 STEP handoff 전에 unite가 끝난 exact named export body여야 한다.
- ferrite-family child가 ungrouped 상태로 scene root에 노출되면 안 된다.
- terminal stub는 `*_stub_in`, `*_stub_out` 두 개만 존재한다. input stub는 wall-side `t0`,
  output stub는 coil-side `t{N-1}`에서 각각 `-Y` 방향으로 `5.0 mm` owner 바깥으로 돌출한다.
- terminal metadata는 `kind = "stub_port"`와 stub body name, `(y, z)` endpoints, metadata-only port-sheet vertices를
  pre-unite source segment 라벨(`*_stub_in/out`) 기반 canonical source로 가진다.

## Invariants / fail-fast
- `pcb_total_thickness_mm > copper_thickness_mm > 0`
- `turn_count >= 2`
- `0 < metal_fill_factor <= 0.6`
- total thickness는 owner thickness budget 안에 들어가야 한다.
- pre-unite body labels는 unique하고 exact-name order contract를 유지해야 한다.
- bridge body는 alternating `Y=max/min` serpentine sequence를 유지한다.
- bridge/slab/copper pair는 positive-volume intersection이 없어야 하며 face/edge touch만 허용한다.
- merged stack ferrite-family는 STEP export 계약상 label당 exactly one united named body여야 한다.
- ferrite-family connector lane은 material별로 분리된 Z band를 사용해 material 간 positive-volume overlap을 만들지 않는다.
- `pcb_wall`, `pcb_coil`은 기존대로 label당 exactly one solid를 유지해야 한다.
- ferrite group member 목록은 ferrite family flat exact-name contract와 같은 label set/순서를 공유해야 한다.
- copper group member 목록은 role-local united copper body 하나와 exact match해야 한다.
- final handoff/임포트/메시 payload에서도 pre-unite 라벨(`*_copper_wall_t*`, `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`)이 body list에 노출되지 않는다.
- import 후 generic `SOLID*`로 분해되는 handoff는 export contract violation이다.
- outer bounds는 owner `YZ` footprint를 유지하되 `min_y`만 `-5.0 mm` overhang를 허용한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- shared module이 active contract owner이므로 TX/RX drift를 role별 helper에 따로 분기해 쌓지 않는다.
- ferrite-family를 `Compound(children=...)`만으로 남겨두면 AEDT import가 child를 `SOLID*`로 풀 수 있으므로 canonical handoff로 취급하지 않는다.
- geometry/export owner는 `shoe_depth_mm`를 무시하지만 spec layer가 아직 field를 가질 수 있으므로,
  later cleanup 전까지 "parsed but geometry-inert" 상태를 깨지 않도록 주의한다.
- equal stripe contract(`wall=N / coil=N`)를 bridge/stub/metadata와 같이 유지해야 한다.
- `src/peetsfea/type2_plate_stack.py`는 800줄 초과 파일이다. 실질적 Python 변경 전에는 분할 필요성을 먼저 검토한다.
