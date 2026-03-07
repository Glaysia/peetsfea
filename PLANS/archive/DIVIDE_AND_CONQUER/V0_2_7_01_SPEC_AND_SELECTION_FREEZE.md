# V0.2.7 - 01 Spec And Selection Freeze

## 문서 메타
- 버전: `V0.2.7`
- 상태: `Planned (분할 문서)`
- 원본 참조: `PLANS/V0_2_7.md`

## 목적
- `source/repro/dataset` 생성의 입력 계약과 선택값 고정 로직을 코드 레벨에서 먼저 확정한다.
- 이후 단계에서 zip export와 옵션 산출물 게이팅을 붙일 수 있도록 실행 계약의 중심 타입을 정리한다.

## 수정 대상 코드 (파일 경로 고정)
- `src/peetsfea/pipeline/run_design.py`
- `src/peetsfea/types/manifest.py` (또는 동급의 신규 타입 파일)
- `src/peetsfea/spec/resolver/*` (필요 최소 변경만 허용)

## 인터페이스/타입 변경
- `SUPPORTED_SPEC_VERSION`를 `0.2.7`로 상향한다.
- `RunConfig`에 아래 옵션 필드를 추가한다.
  - `emit_manifest_json: bool = False`
  - `emit_geometry_metadata_json: bool = False`
  - `export_zip: bool = True`
- `run()` 반환 계약을 `Manifest` 중심에서 `RunResult` 중심으로 전환한다.
- 신규 타입을 도입한다.
  - `ReproSnapshot`
  - `DatasetSnapshot`
  - `RunResult`

## 구현 규칙
- 선택 완료 직후 메모리 스냅샷을 생성한다.
  - `repro.toml`: 모든 가변 경로를 `count=1`로 고정한 TOML bytes
  - `dataset.toml`: 선택값 고정 + `output.*=-1` + `simulation.timeout_sec=7200` TOML bytes
  - `source.toml`: 입력 원본 TOML raw bytes 그대로 사용
- 본 단계에서는 zip 파일 생성 및 파일 배치 작업을 수행하지 않는다.

## 테스트 추가/수정
- 기존 확장: `tests/test_manifest_determinism.py`
  - 동일 seed에서 동일 snapshot이 생성되는지 검증
- 신규: `tests/test_v027_snapshot_contract.py`
  - `repro`의 `count=1` 강제 검증
  - `dataset`의 `output.*=-1`, `simulation.timeout_sec=7200` 검증
  - `source` 바이트 동일성 검증

## 완료 조건 (DoD)
- `run()` 결과에서 snapshot 3종을 타입 안정적으로 접근할 수 있다.
- 0.2.7 입력 스펙에서 snapshot 계약을 깨는 케이스가 테스트에서 즉시 실패한다.
- 본 단계 단독으로는 zip/옵션 산출물 정책을 구현하지 않는다.

## 비범위 (Out of scope)
- `manifest_{design_id}.json`, `geometry_metadata_{design_id}.json` 생성 정책 변경
- `<design_id>.zip` 생성 및 payload 구성
- acceptance 자동화 테스트의 최종 매핑

다음 단계: [V0_2_7_02_GEOMETRY_OUTPUT_GATING.md](./V0_2_7_02_GEOMETRY_OUTPUT_GATING.md)
