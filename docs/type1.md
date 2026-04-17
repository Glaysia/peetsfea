---
title: type1 문서
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type1
---

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
- `ferrite`: 전역 ferrite on/off와 coil-footprint 기준 RX/TX ferrite 두께, 재질 기본값. `ferrite.tx_gap_mm`가 TX ferrite gap의 canonical sampled owner이고, 기본 예제는 `3.1..12.0`, `count=8`이다. TX ferrite는 최하단 TX XY FR4 아래 그 gap을 유지하고 TX coil copper, TX bridge object, TX FR4 live object와 비접촉이어야 한다.
- `coil_shape`, `coil_groups_params`: 그룹별 코일 형상 및 파생 파라미터 제어
- 기본 runnable example에서 `tx.region.z_parts.vertical_z_mm`는 `5..15`, `count=11`로 샘플링된다. 현재 `tx_vertical` 실제 높이는 `min(coil_shape.neo_tx_vertical.outer_y, tx.region.z_parts.vertical_z_mm)`이므로, 기본 샘플에서는 사실상 `tx_region_vertical_z_mm`가 높이 owner처럼 동작한다.
- `coil_placement`: 배치 계약 제어. 기본 예제는 `coil_placement.neo_tx_dd_top_offset_ratio`를 `0.01..0.6`, `count=30`으로 두고, 이는 `tx.region.z_parts.dd_z_mm` 대비 DD 코일 top의 하강 비율이다. `coil_placement.tx_vertical_orientation_mode`는 이제 `0=no tx_vertical`, `1=ZX tx_vertical`을 뜻하고, 기본 예제는 두 상태를 모두 샘플링한다. 기본 예제의 `coil_groups.tx_vertical.count_range`는 여전히 ZX vertical requested-count owner로 `1..6`을 샘플링하지만, orientation mode가 `0`이면 sampling owner는 유지한 채 realized `selected_count`는 `0`이 된다. 공개 스펙은 더 이상 `coil_placement.tx_vertical_plane`를 받지 않으며 realized plane은 현재 내부적으로 `ZX`로 고정된다. 공통 geometry key는 neo migration을 위해 `coil_shape.neo_tx_vertical.*`, `coil_groups_params.neo_tx_vertical.*`로 옮겼고, vertical 전용 배치 key는 아직 `tx_vertical_*` 이름을 유지한다. `coil_placement.neo_tx_dd_right_terminal_path`와 `coil_placement.neo_tx_dd_left_terminal_path`는 neo TX DD 좌우 코일의 terminal-path 계약이며, `coil_placement.neo_tx_vertical_zx_terminal_path`는 ZX/XZ 기준 neo TX vertical migration용 terminal-path 계약이다. 모든 값 형식은 `<start>_<cw|ccw>_to_<end>`이고, 기본 예제는 `B_ccw_to_c`를 사용한다. 이 ZX/XZ 계약은 `+Y`에서 바라보고 `+Z`가 위, `+X`가 왼쪽인 시점 기준으로 읽는다. no-vertical 모드에서는 finalized TX DD 객체를 `Y`축 기준으로 기울여 현재 TX-region top 계약을 맞춘다.
- `tx_dd`가 4개 인스턴스(2층)로 해석되면 아래층은 같은 turn/trace/gap을 유지하되 centerline box를 한 pitch만큼 줄여 위층 trace 사이 gap 중심 쪽으로 interleave된다.
- `constraints`: 샘플 선택/배치 가능성/토폴로지 제약 검증
- `pcbs`: fixed-topology 계약에 따른 보드 present/mount 정규화. 정규화로 소거되는 field는 독립 sampled dimension으로 허용하지 않는다.

## type1 사용 시 알아야 할 제한
- 이 계약은 설계 생성 중심이며 시뮬레이션 결과 채움은 범위 밖이다.
- `manifest_<design_id>.json`, `geometry_metadata_<design_id>.json`은 기본 비활성이다.
- 장기 하위호환은 보장하지 않으며 릴리즈에서 계약이 바뀔 수 있다.

## 빠른 확인 포인트
- 입력 스펙: `examples/type1.toml`
- 실행 진입점: `entry/sample.py` -> `entry/build.py`, 또는 미리 생성된 manifest를 GUI-visible replay로 확인하는 `entry/sample_build.py`
- 기본 테스트: `run/` 디렉터리에서 `../.venv/bin/pytest -q ../tests`
