# V0.2.7 - 04 Acceptance Automation

## 문서 메타
- 버전: `V0.2.7`
- 상태: `Planned (분할 문서)`
- 원본 참조: `PLANS/V0_2_7.md`

## 목적
- V0.2.7 수용 기준을 테스트 케이스로 고정해 릴리즈 판정을 자동화한다.
- 문서 항목과 테스트 케이스 ID를 1:1로 매핑해 실패 원인을 즉시 역추적 가능하게 한다.

## 수정 대상 코드 (파일 경로 고정)
- `tests/test_v027_snapshot_contract.py`
- `tests/test_v027_optional_outputs.py`
- `tests/test_v027_zip_payload.py`
- 필요 시 `tests/conftest.py` (마커/공통 fixture)

## 인터페이스/타입 변경
- 테스트 계층을 아래 2개로 분리한다.
  - pure-Python 계약 테스트 (기본 CI)
  - Pyaedt 연동 테스트 (옵션 마커 분리)
- acceptance 케이스는 `AC-01`~`AC-07` ID를 사용해 문서와 동일 식별자를 유지한다.

## 테스트 추가/수정
- `AC-01`: 기본 실행 시 zip 1개 생성
- `AC-02`: zip payload 4개 정확성
- `AC-03`: `repro`의 `count=1` 강제
- `AC-04`: `dataset`의 `output.*=-1`, `simulation.timeout_sec=7200`
- `AC-05`: `source` 바이트 동일 복사
- `AC-06`: 기본값에서 manifest/geometry metadata 미생성
- `AC-07`: 옵션 활성 시에만 manifest/geometry metadata 생성 허용

## 완료 조건 (DoD)
- `AC-01`~`AC-07`이 자동 테스트로 모두 존재한다.
- 각 케이스 실패 메시지가 해당 계약 문구를 직접 포함한다.
- 기본 CI에서 pure-Python 계약 테스트가 통과하고, 옵션 실행에서 Pyaedt 연동 테스트가 분리 동작한다.

## 비범위 (Out of scope)
- 새로운 제품 기능 추가
- 0.2.7 계약 자체 변경
- 문서 외부의 릴리즈 프로세스 자동화 도구 도입

이전 단계: [V0_2_7_03_PACKAGE_EXPORT_CONTRACT.md](./V0_2_7_03_PACKAGE_EXPORT_CONTRACT.md)
