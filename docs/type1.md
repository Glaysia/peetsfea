# type1 문서

## type1이 무엇인가
- `type1`은 TV/벽면 환경 IPT 기준 설계다.
- 송신부(TX)는 `tx_dd`, `tx_vertical` 그룹을 사용하고, 수신부(RX)는 `rx_dd` 그룹을 사용한다.
- 코일 그룹은 PCB 배치 규칙과 함께 선택/정규화되어 HFSS 기하 생성 입력으로 사용된다.

## 무엇을 생성하나
- HFSS 설계 파일(`.aedt`)을 생성한다.
- zip 산출물은 현재 임시 비활성화 상태다.
- 아래 4개 payload는 실행 스냅샷으로 유지된다.
  - `<design_id>.aedt`: HFSS 설계 본체
  - `<design_id>.repro.toml`: canonical sampled owner가 모두 동결된 exact replay 스냅샷
  - `<design_id>.dataset.toml`: 최종 설계에 영향을 주는 canonical sampled owner만 담는 exact sampled-coordinate ledger(`output.*=-1`, `timeout_sec=7200`)
  - `<design_id>.source.toml`: 실행에 사용한 원본 TOML 복사본
- `design_id`는 `seed_uniqueHash_spaceHash_attempt` 형식이다. `uniqueHash`는 realized design identity이고, `spaceHash`는 원본 `source.toml` sampling space identity다.

## 입력 스펙에서 중요한 블록
- `tv`, `tx.region`, `rx.region`: 장면/영역 크기와 배치 기준
- `ferrite`: 전역 ferrite on/off와 coil-footprint 기준 RX/TX ferrite 두께, 재질 기본값. `ferrite.tx_gap_mm`가 TX ferrite gap의 canonical sampled owner이고, 기본 예제는 `3.1..12.0`, `count=8`이다. TX ferrite는 최하단 TX XY FR4 아래 그 gap을 유지하고 TX coil copper, TX bridge object, TX port sheet object, TX FR4 sheet object와 비접촉이어야 한다.
- `coil_shape`, `coil_groups_params`: 그룹별 코일 형상 및 파생 파라미터 제어
- 기본 runnable example에서 `tx.region.z_parts.vertical_z_mm`는 `5..15`, `count=11`로 샘플링된다. 현재 `tx_vertical` 실제 높이는 `min(coil_shape.tx_vertical.outer_y, tx.region.z_parts.vertical_z_mm)`이므로, 기본 샘플에서는 사실상 `tx_region_vertical_z_mm`가 높이 owner처럼 동작한다.
- `coil_placement`: 배치 계약 제어. 기본 예제는 `coil_placement.tx_dd_top_clearance_ratio`를 `0.0..0.3`, `count=10`으로 두고, 이는 `tx.region.z_parts.dd_z_mm` 대비 DD 코일 top의 하강 비율이다. `coil_placement.tx_vertical_layout_mode`는 `1=ZX`, `2=YZ`를 뜻하고, mode 2에서는 `coil_spacing.tx_vertical_mode2_pair_spacing_ratio`가 RX-DD-style vertical DD pair의 내부 gap을 `tx.region.outer_h_mm` 기준 `0.0..0.03`, `count=25`로 제어하며, `coil_placement.tx_vertical_mode2_x_ratio_to_tx_dd_center`가 그 pair의 `X`를 underlying TX DD 폭의 RX-far `70%..100%`, `count=10` 구간으로 제어한다. 공개 path 이름은 유지하지만 실제 식은 `tx_dd_min_x + ratio * tx_dd_outer_x`다. 기본 예제의 `coil_groups.tx_vertical.count_range`는 legacy ZX mode용으로 `1..6`을 샘플링하고, mode 2에서는 보드당 DD pair 1개만 실현하므로 realized `selected_count=1`로 clamp 된다. 공개 스펙은 더 이상 `coil_placement.tx_vertical_plane`를 받지 않으며 realized plane만 내부에서 파생한다.
- 기본 runnable scene은 기존 scene-anchor 공식을 유지한 채 `scene_anchor.shelf_height_mm = 461.0`으로 맞춰 nominal `TX-region top -> RX-region bottom` gap을 `50 mm`로 둔다.
- mode 2 (`YZ`)의 실제 구동 전류 방향은 `+X` 시점 기준으로 오른쪽 `(+Y)` half가 시계방향(`-X` local B), 왼쪽 `(-Y)` half가 반시계방향(`+X` local B)으로 고정된다.
- mode 2 (`YZ`)는 현재 legacy `Y`-side bridge no-pierce guard를 적용하지 않는다. 그 guard는 `ZX` 배치 계약으로만 유지된다.
- `coil_groups_params.{tx_dd,tx_vertical,rx_dd}.turn_count_max`는 모두 기본 `2..3` 범위를 사용하며, 런타임도 `3`까지 허용한다.
- `outputs`: AEDT output variable과 단일 data-table report의 SSOT. 기본 예제에는 `S22_mag_ratio`와 WPT 파생 효율 지표 8개가 포함된다.
- `outputs`의 `eta_*_from_*`, `eta_s21_two_sided_norm_ratio`는 normalized proxy metric이라 acceptance term이 0에 가까우면 불안정해질 수 있다.
- `tx_dd`가 4개 인스턴스(2층)로 해석되면 아래층은 같은 turn/trace/gap을 유지하되 centerline box를 한 pitch만큼 줄여 위층 trace 사이 gap 중심 쪽으로 interleave된다.
- `constraints`: 샘플 선택/배치 가능성/토폴로지 제약 검증
- `pcbs`: fixed-topology 계약에 따른 보드 present/mount 정규화. 정규화로 소거되는 field는 독립 sampled dimension으로 허용하지 않는다.

## type1 사용 시 알아야 할 제한
- 이 계약은 설계 생성 중심이며 시뮬레이션 결과 채움은 범위 밖이다.
- `manifest_<design_id>.json`, `geometry_metadata_<design_id>.json`은 기본 비활성이다.
- 장기 하위호환은 보장하지 않으며 릴리즈에서 계약이 바뀔 수 있다.

## 빠른 확인 포인트
- 입력 스펙: `examples/type1.toml`
- 실행 진입점: `entry/multi_sample.py` -> `entry/build.py` 또는 `entry/multi_build.py`
- 기본 테스트: `run/` 디렉터리에서 `../.venv/bin/pytest -q ../tests`
