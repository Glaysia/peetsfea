---
title: type2_single_coil_underlay.py
created: 2026-04-20 @ 00:00
updated: 2026-05-06 @ 00:00
tags:
  - rx
  - non-model
---

# type2_single_coil_underlay.py

## Source
- Path: `src/peetsfea/type2_single_coil_underlay.py`
- Code note path: `sdd/code/src/peetsfea/type2_single_coil_underlay.py.md`
- Status: active

## 역할
- RX single-coil backing/context geometry helper다.
- TX inner actual-region underlay geometry helper다.
- TX inner void YZ sheet-stack geometry helper다.
- Type2 single-coil ferrite/PET_PSA priority boolean-clearance helper다.
- TX outer prism-local void sheet-stack geometry helper다.
- TX outer prism-local bottom-underlay sheet-stack geometry helper다.

## 책임
- `tx_inner_single_coil` 하위층 하부 적층 바디를 생성한다. `-Z` 방향으로 각 반복마다 `PET_PSA`(상단)→`MULL12060ferrite`(하단) 순으로 쌓으며 `tx_underlay_pet_psa_u{n}` / `tx_underlay_ferrite_u{n}` 라벨을 붙인다.
- `tx_inner_single_coil` 페라이트/언더레이 그룹 이름을 `g_ferrite_tx`로 반환해 export ledger에 반영한다.
- 스택의 상단 Z(첫 PET의 MAX Z)는 `fit_envelope.outer_bounds_min_z`와 정렬한다.
- `tx_inner_single_coil` void 내부 YZ 스택을 생성한다. body prefix는 `tx_void_ferrite_u{n}` / `tx_void_pet_psa_u{n}`이며 X방향으로 최대 적층하고, Y는 scene layer에서 계산한 central corridor bounds를 따른다. 생성 여부는 scene layer의 `void_stack_present` 판정이 소유한다.
- ordered scene child tuple에서 ferrite/PET_PSA tool과 PCB/FR4 blank를 식별하고, build123d/OCC cut으로 PCB/FR4 blank만 절단한 새 ordered tuple을 반환한다.
- `tx_outer_single_coil` void 내부 prism-local 스택을 생성한다. body prefix는 `tx_outer_void_ferrite_u{n}` / `tx_outer_void_pet_psa_u{n}`이며 raw top을 prism-local top보다 위로 뻗긴 뒤 outer scene builder가 top-face clipping과 tilt transform을 적용한다.
- `tx_outer_single_coil` 하부 prism-local 스택을 생성한다. body prefix는 `tx_outer_underlay_pet_psa_u{n}` / `tx_outer_underlay_ferrite_u{n}`이며 inner underlay와 같은 PET/PSA→ferrite ordering을 사용한다.

## Canonical state
- `resolve_tx_inner_single_coil_underlay_placement_descriptor`는 `owner_spec`와 실제 영역 footprint (`fit_envelope.outer_bounds_*`)를 검증한 뒤 반복 횟수/두께 합이 `tx_inner_region` 바닥을 침범하지 않으면 descriptor를 만든다.
- `build_tx_inner_single_coil_underlay_shapes`는 반복 수가 0이면 빈 튜플을 반환하고, 1 이상이면 PET+ferrite 쌍을 `underlay_repeat_count` 순서대로 생성한다.
- `resolve_tx_outer_single_coil_underlay_placement_descriptor` validates the prism-local outer design/actual footprint and derived stack thickness against the virtual outer owner thickness before creating the shared underlay descriptor.
- TX outer central void stack and bottom underlay stack are derived from inner repeat/thickness state and use separate outer label prefixes.
- TX inner void stack descriptor는 realized void X world bounds, copper-free central corridor Y world bounds, `tx_inner_actual_region.min_z`, `tx_region.max_z`, nominal PET/PSA/ferrite thickness를 canonical state로 가진다.
- boolean-clearance helper의 canonical state는 caller가 넘긴 ordered scene shapes, explicit ferrite/PET_PSA tool labels/groups 또는 narrow label predicate, 그리고 explicit PCB/FR4 blank labels다.

## Invariants / fail-fast
- 잘못된 `tx_inner_single_coil` footprint/thickness/반복 값은 즉시 실패한다.
- `tx_inner_single_coil` underlay는 X/Y footprint를 `fit_envelope.outer_bounds_*`에서 가져오며, 물리적 모델링 bbox(physical modeled body bounds)에서 유도하지 않는다.
- 쌓인 스택의 최하단 Z가 `tx_inner_region` bottom을 밑돌면 즉시 실패한다.
- `tx_inner_single_coil`의 underlay는 페라이트 전용/하우스홀딩(air) 레이어 없이 PET+ferrite 2중 레이어만 생성한다.
- void YZ stack은 `void.min_x`에서 ferrite로 시작해 PET/PSA와 교대하며, 마지막 layer는 남은 X 폭에 맞게 잘라 정확히 `void.max_x`에서 끝난다. Y span은 descriptor가 제공한 central corridor 전체를 사용한다.
- outer void stack도 같은 sheet ordering and X truncation contract를 따르되, raw Z는 prism-local top을 한 PET/PSA+ferrite pair만큼 넘어선다. scene 조립 단계가 top-face clipping과 최종 회전/이동을 적용한다.
- outer bottom underlay stack must use the outer design/actual footprint, stack downward in local `-Z`, and fail if its derived thickness cannot fit inside the virtual outer owner thickness.
- 레이블 길이 제한(<=32), 볼륨 양의 값, 바디 수 일관성 등 기존 underlay 실패 규칙은 유지한다.
- boolean-clearance helper는 입력/출력 top-level body count와 label order를 보존하며, ferrite/PET_PSA tools는 절단하지 않고 PCB/FR4 blanks만 절단한다.
- expected cut path에서 tool 또는 blank가 비어 있으면 즉시 실패한다.
- label 중복, 무라벨 shape, group child label 중복, cut 결과 empty/invalid/non-positive/non-single-solid 상태는 즉시 실패한다.

## Collaborators
- [type2_single_coil_scene.py](type2_single_coil_scene.py.md)
- [test_type2_single_coil_underlay_boolean_clearance.py](../../tests/type2/test_type2_single_coil_underlay_boolean_clearance.py.md)
- [0.2.24 Type2 TX Inner Actual Underlay Stack](../../../plans/0.2.24-type2-tx-inner-actual-underlay-stack.md)
- [0.2.24 Type2 TX Inner Void YZ Stack](../../../plans/0.2.24-type2-tx-inner-void-yz-stack.md)
- [Type2 Ferrite FR4 Boolean Clearance](../../../plans/0.2.24-type2-ferrite-fr4-boolean-clearance.md)
- [0.2.24 Type2 TX Outer Void Stack](../../../plans/0.2.24-type2-tx-outer-void-stack.md)
