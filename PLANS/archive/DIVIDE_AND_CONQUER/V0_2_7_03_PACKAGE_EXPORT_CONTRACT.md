# V0.2.7 - 03 Package Export Contract

## 문서 메타
- 버전: `V0.2.7`
- 상태: `Planned (분할 문서)`
- 원본 참조: `PLANS/V0_2_7.md`

## 목적
- `설계 1개 = zip 1개` 계약을 실제 파일 산출 규칙으로 확정한다.
- payload 구성을 deterministic하게 고정해 데이터 파이프라인의 재현성을 보장한다.

## 수정 대상 코드 (파일 경로 고정)
- `src/peetsfea/pipeline/package_export.py` (신규)
- `src/peetsfea/pipeline/run_design.py`
- `src/peetsfea/__init__.py` (필요 시 export 정리)

## 인터페이스/타입 변경
- `RunResult.zip_path`를 표준 산출물 경로로 사용한다.
- `export_zip=True`일 때만 `<design_id>.zip` 생성을 수행한다.
- zip export 함수는 입력으로 `design_id`, `aedt_path`, snapshot bytes를 받는 순수 인터페이스로 정의한다.

## 구현 규칙
- zip payload는 아래 4개로 고정한다.
  - `<design_id>.aedt`
  - `<design_id>.repro.toml`
  - `<design_id>.dataset.toml`
  - `<design_id>.source.toml`
- 파일명/확장자/인코딩을 deterministic하게 고정한다.
- 압축 전 임시 파일 쓰기 위치는 `run/` 하위로 제한한다.
- 레거시 옵션 산출물(`manifest`, `geometry_metadata`)은 zip 기본 payload에 포함하지 않는다.

## 테스트 추가/수정
- 신규: `tests/test_v027_zip_payload.py`
  - zip 1개 생성 검증
  - 내부 payload 4개 정확성 검증
  - `dataset` 규칙값 검증(`output.*=-1`, `simulation.timeout_sec=7200`)
- 반복 실행 시 payload 목록/내용 해시가 동일한지 검증한다.

## 완료 조건 (DoD)
- `run` 1회당 zip 1개가 표준 산출물로 생성된다.
- payload 4개 외 파일이 기본 zip에 포함되지 않는다.
- 동일 입력(seed 포함)에서 zip 내부 계약이 안정적으로 재현된다.

## 비범위 (Out of scope)
- Pyaedt 시뮬레이션 실행 결과 채우기
- long-term 스펙 개편(`V0_3_x`) 작업
- acceptance 테스트의 운영 분류/마커 정책 확정

이전 단계: [V0_2_7_02_GEOMETRY_OUTPUT_GATING.md](./V0_2_7_02_GEOMETRY_OUTPUT_GATING.md)  
다음 단계: [V0_2_7_04_ACCEPTANCE_AUTOMATION.md](./V0_2_7_04_ACCEPTANCE_AUTOMATION.md)
