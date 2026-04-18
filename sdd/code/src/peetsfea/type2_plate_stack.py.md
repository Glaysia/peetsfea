---
title: type2_plate_stack.py
created: 2026-04-19 @ 21:42
updated: 2026-04-20 @ 00:32
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
- Related feature plans: [[sdd/plans/0.2.22-type2-rx-plate-stack-striped-copper]], [[sdd/plans/0.2.22-type2-tx-rx-shared-plate-stack-import-only]], [[sdd/plans/0.2.22-type2-plate-stack-bridge-non-overlap-export]]

## 역할
- active TX/RX plate-stack geometry contract의 canonical owner다.
- role config 차이만으로 TX `tx_plate_stack`와 RX `rx_plate_stack` scene data를 모두 만든다.

## 입력 / 출력
- 입력: plate-stack modeled spec, placement owner spec
- 출력: labeled solids/nested sandwich compounds, canonical coordinates, `stub_port` terminal metadata를 포함한 modeled scene data

## Canonical state
- TX는 `tx_region` full `YZ`, `min_x` anchor, `+X` stack를 사용한다.
- RX는 `rx_region_max` full `YZ`, `min_x` anchor, `+X` stack를 사용한다.
- wall-side copper turn count는 `N`, coil-side copper turn count는 `N - 1`이다.
- active conductor 높이는 full owner `Z` span이다.
- exact flat body order는 `*_copper_wall_t*`, `*_pcb_wall`, `*_stack_*`, `*_pcb_coil`,
  `*_copper_coil_t*`, `*_bridge_s*`, `*_stub_in/out`다.
- bridge body의 X span은 wall copper와 coil copper 사이 interior-only 구간이다.
- `*_pcb_wall`, `*_stack_*`, `*_pcb_coil`은 bridge가 지나는 edge strip + Z window를 notch로 비워 bridge와 positive-volume overlap이 없다.
- ferrite family는 role당 정확히 1개 group metadata/compound만 export한다:
  TX `g_ferrite_tx`, RX `g_ferrite_rx`.
- ferrite group member order는 생성 순서 그대로 flatten된
  `*_stack_pet_psa_uN -> *_stack_ferrite_uN -> *_stack_air_uN` 전체 시퀀스다.
- terminal stub는 `*_stub_in`, `*_stub_out` 두 개만 존재하고, 둘 다 wall-side stripe에서 `+Y` 방향으로 `5.0 mm` owner 바깥으로 돌출한다.
- terminal metadata는 `kind = "stub_port"`와 stub body name, `(y, z)` endpoints, metadata-only port-sheet vertices를 canonical source로 가진다.

## Invariants / fail-fast
- `pcb_total_thickness_mm > copper_thickness_mm > 0`
- `turn_count >= 2`
- `0 < metal_fill_factor <= 0.5`
- total thickness는 owner thickness budget 안에 들어가야 한다.
- body labels는 unique하고 exact-name order contract를 유지해야 한다.
- bridge body는 alternating `Y=max/min` serpentine sequence를 유지한다.
- bridge/slab/copper pair는 positive-volume intersection이 없어야 하며 face/edge touch만 허용한다.
- notch 적용 slab body도 label당 exactly one solid를 유지해야 한다.
- ferrite group member 목록은 ferrite family flat exact-name contract와 같은 label set/순서를 공유해야 한다.
- outer bounds는 owner `YZ` footprint를 유지하되 `max_y`만 `+5.0 mm` overhang를 허용한다.

## Collaborators
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/type2_step_scene.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_partition.py]]
- [[sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]
- [[sdd/code/tests/backend_em/test_type2_step_import_pipeline.py]]

## 변경 시 주의점
- shared module이 active contract owner이므로 TX/RX drift를 role별 helper에 따로 분기해 쌓지 않는다.
- geometry/export owner는 `shoe_depth_mm`를 무시하지만 spec layer가 아직 field를 가질 수 있으므로,
  later cleanup 전까지 "parsed but geometry-inert" 상태를 깨지 않도록 주의한다.
- asymmetric `wall=N / coil=N-1` 계약을 bridge/stub/metadata와 같이 유지해야 한다.
