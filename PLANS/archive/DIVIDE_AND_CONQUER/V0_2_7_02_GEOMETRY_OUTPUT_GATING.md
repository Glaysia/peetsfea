# V0.2.7 - 02 Geometry Output Gating

## 문서 메타
- 버전: `V0.2.7`
- 상태: `Planned (분할 문서)`
- 원본 참조: `PLANS/V0_2_7.md`

## 목적
- geometry/build 경로의 side effect 산출물을 0.2.7 정책으로 제어한다.
- 기본 실행에서 JSON 부가 산출물 생성이 발생하지 않도록 게이트를 명시한다.

## 수정 대상 코드 (파일 경로 고정)
- `src/peetsfea/backend/pyaedt/geometry/build.py`
- `src/peetsfea/backend/pyaedt/geometry/metadata.py`
- `run.py`

## 인터페이스/타입 변경
- `RunConfig.emit_manifest_json` / `RunConfig.emit_geometry_metadata_json`를 실제 출력 게이트로 연결한다.
- `RunResult.manifest_path`, `RunResult.geometry_metadata_path`는 옵션 비활성 시 `None`을 허용한다.

## 구현 규칙
- 기본값에서 아래 파일을 생성하지 않는다.
  - `manifest_{design_id}.json`
  - `geometry_metadata_{design_id}.json`
- 옵션 활성 시에만 레거시 JSON 산출물 생성을 허용한다.
- `run.py` 실패 정리 로직은 기본 정책 기준으로 동작한다.
  - 기본값에서는 JSON 파일 삭제를 기대하지 않는다.
  - 옵션 활성 시 생성된 JSON만 조건부 정리한다.

## 테스트 추가/수정
- 신규: `tests/test_v027_optional_outputs.py`
  - 기본 실행 시 manifest/geometry metadata 미생성 검증
  - 옵션 활성 시 생성 허용 검증
- 기존 manifest 중심 테스트는 레거시 옵션 전제(`emit_manifest_json=True`)로 분리/명시한다.

## 완료 조건 (DoD)
- 기본 실행 시 `.aedt + in-memory snapshot`까지만 생성된다.
- JSON 산출물 생성 여부가 옵션 값과 정확히 일치한다.
- 옵션 비활성 상태에서 JSON 파일이 생성되면 테스트가 실패한다.

## 비범위 (Out of scope)
- zip payload 파일 생성/패키징
- snapshot 내용 규칙의 상세 구현 변경
- acceptance 최종 시나리오의 전수 자동화

이전 단계: [V0_2_7_01_SPEC_AND_SELECTION_FREEZE.md](./V0_2_7_01_SPEC_AND_SELECTION_FREEZE.md)  
다음 단계: [V0_2_7_03_PACKAGE_EXPORT_CONTRACT.md](./V0_2_7_03_PACKAGE_EXPORT_CONTRACT.md)
