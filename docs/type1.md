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
- `ferrite`: 전역 ferrite on/off와 coil-footprint 기준 RX/TX ferrite 두께, 재질 기본값
- `coil_shape`, `coil_groups_params`: 그룹별 코일 형상 및 파생 파라미터 제어
- `tx_dd`가 4개 인스턴스(2층)로 해석되면 아래층은 같은 turn/trace/gap을 유지하되 centerline box를 한 pitch만큼 줄여 위층 trace 사이 gap 중심 쪽으로 interleave된다.
- `constraints`: 샘플 선택/배치 가능성/토폴로지 제약 검증
- `pcbs`: fixed-topology 계약에 따른 보드 present/mount 정규화. 정규화로 소거되는 field는 독립 sampled dimension으로 허용하지 않는다.

## type1 사용 시 알아야 할 제한
- 이 계약은 설계 생성 중심이며 시뮬레이션 결과 채움은 범위 밖이다.
- `manifest_<design_id>.json`, `geometry_metadata_<design_id>.json`은 기본 비활성이다.
- 장기 하위호환은 보장하지 않으며 릴리즈에서 계약이 바뀔 수 있다.

## 빠른 확인 포인트
- 입력 스펙: `examples/type1.toml`
- 실행 진입점: `multi_sample.py` -> `build.py` 또는 `multi_build.py`
- 기본 테스트: `run/` 디렉터리에서 `../.venv/bin/pytest -q ../tests`
