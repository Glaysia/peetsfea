# PHASE2B - band_ratio 전환 + tx_vertical FR4 다층 집계 수정

## 목표
- 그룹 지오메트리 입력을 절대 두께(`band_thickness_mm`)에서 비율(`band_ratio`)로 전환한다.
- tx_vertical 다중 인스턴스/PCB 배치 시 FR4가 한쪽에만 생성되는 집계 버그를 수정한다.

## 스코프
- 기존 PHASE2(DD mirror)와 독립적으로 진행한다.
- 적용 범위는 resolver/spec/geometry/tests/docs.

## 핵심 변경
1. spec_version: `0.1.6` -> `0.1.7`
2. `coil_groups_params.<kind>` 키:
   - 제거: `band_thickness_mm`
   - 추가: `band_ratio`
3. 파생식:
   - `effective_outer_y = min(outer_y, tx_region_vertical_z_mm)` for tx_vertical, else `outer_y`
   - `base_outer = min(outer_x, effective_outer_y)`
   - `band_mm = band_ratio * base_outer`
   - `pitch = band_mm / turn_count_max`
   - `trace = pitch * metal_ratio`
   - `gap = pitch * (1 - metal_ratio)`
4. FR4 집계 키 변경:
   - 기존: `(board_id, plane)`
   - 변경: `(board_id, plane, layer_axis_key)`
   - `XY`: z center, `YZ`: x center, `ZX`: y center 기준 layer 분리

## 검증 포인트
- `seed=10` 및 seed sweep에서 생성 안정성 유지
- tx_vertical 다중 배치에서 FR4 box가 복수 생성되고 y-layer별로 분리되는지 확인
- 기존 XY/YZ 보드 생성 회귀 없음

## 완료 기준
- `selected_group_geometry`가 `band_ratio`를 기록한다.
- `tx_vertical` 다중 배치에서 FR4가 하나만 생기지 않는다.
- 관련 테스트가 통과한다.
