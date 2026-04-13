# 0.2.22 Build123d 기반 AEDT 임포트 전환 계획

## 목적

현재 geometry build는 PyAEDT를 통해 AEDT 내부에서 직접 형상을 만들고 수정하는 흐름을 중심으로 되어 있다. 이 방식은 최종 EM 해석 환경과 바로 이어진다는 장점은 있지만, 형상 iteration 속도가 느리고 디버깅 피드백이 무겁다.

0.2.22 이후의 전환 목표는 `build123d`를 1차 geometry authoring backend로 사용하고, AEDT/PyAEDT는 생성된 geometry artifact를 import한 뒤 EM 해석, 포트/경계/리포트 설정, 결과 추출을 담당하도록 역할을 나누는 것이다.

이 문서는 구현 착수 전에 방향과 검증 항목을 고정하기 위한 계획 문서다. 이 단계에서는 runtime code, TOML spec, dataset/repro artifact 계약을 변경하지 않는다.

## 현재 문제

- AEDT 내부에서 직접 geometry를 생성하면 단순 형상 수정에도 실행 시간이 크고 피드백이 느리다.
- build 실패가 AEDT session, geometry operation, EM setup 문제와 섞여 나타나서 원인 분리가 어렵다.
- 현재 코일 생성 로직은 type1 토폴로지와 대칭 코일 전제에 많이 묶여 있다.
- 앞으로 새 코일 형상, 새 파라미터, 비대칭 배치, 병렬 코일 구조를 검토하려면 geometry authoring 계층을 더 빠르게 실험할 수 있어야 한다.

## 목표 아키텍처

- TOML spec parsing, deterministic selection, sampling ledger, dataset/repro snapshot 계약은 유지한다.
- geometry build 단계에서 선택된 파라미터를 받아 `build123d` model을 생성한다.
- `build123d` model은 STEP 등 AEDT가 headless 환경에서 안정적으로 읽을 수 있는 중간 artifact로 export한다.
- PyAEDT는 export artifact를 import하고 기존 EM pipeline의 boundary, port, source, analysis, report 단계를 적용한다.
- PyAEDT 호출이 `False`를 반환하거나 import/validation이 실패하면 즉시 예외를 발생시킨다.
- GUI-visible AEDT 검증은 사용자가 별도로 요청한 경우에만 수행한다.

## 전환 단계

1. 단순 solid smoke test
   - `tmp/build123d_smoke` 수준에서 단순 solid를 만들고 STEP export를 확인한다.
   - OCP CAD Viewer로 `build123d` 생성 형상을 빠르게 시각 확인한다.
   - 이 단계는 로컬 실험용이며 runtime contract에 포함하지 않는다.

2. AEDT headless import smoke test
   - STEP artifact를 PyAEDT headless session으로 import하는 최소 경로를 확인한다.
   - import 결과 object name, material assignment, bounding box, modeler object 목록을 검증 대상으로 잡는다.
   - import 실패는 즉시 예외로 처리하고, stale AEDT artifact나 GUI 동작으로 원인을 우회하지 않는다.

3. 기존 type1 코일 일부 재현
   - type1 전체를 한 번에 옮기지 않고, 가장 작은 코일 primitive 하나를 `build123d`로 재현한다.
   - 기존 PyAEDT 직접 생성 결과와 외곽 크기, trace/gap, terminal 후보 위치, artifact export 결과를 비교한다.
   - 성공 기준은 동일한 최종 EM 성능이 아니라, geometry ownership과 import 가능성을 확인하는 것이다.

4. build pipeline 분리 검토
   - 현행 PyAEDT geometry builder와 새 `build123d` authoring path를 한 파일 안에 섞지 않는다.
   - 공통 contract는 selected parameters, artifact paths, imported object registry, EM pipeline input으로 제한한다.
   - import된 object의 canonical coordinates는 생성 시점 metadata로 보존하고, AEDT 내부 geometry에서 역산하지 않는다.

## 코일 재설계 방향

- 현행 대칭 코일 전제는 장기적으로 제거한다.
- 새 코일 spec은 path, turn, terminal, layer, branch 개념을 독립적으로 표현할 수 있어야 한다.
- 새 파라미터 이름과 TOML path는 아직 확정하지 않는다.
- 비대칭 코일의 좌표계, terminal polarity, port naming, dataset owner는 사용자 요구사항이 더 구체화된 뒤 별도 spec 변경 계획에서 결정한다.
- 기존 type1 계약과 새 코일 계약을 동시에 유지해야 하는 경우, preflight에서 지원/미지원 항목을 명확히 보고해야 한다.

## 병렬 코일 실험 축

- 병렬 코일은 저항 감소 후보로 별도 실험 축으로 둔다.
- 병렬 branch는 단순히 geometry를 복제하는 문제가 아니라 포트 정의, 전류 분배, 인덕턴스, 결합, AC 저항, dataset owner가 함께 바뀌는 문제로 취급한다.
- 초기 실험에서는 branch 수, branch 간 간격, terminal merge 방식, 포트 연결 방식을 분리해서 기록한다.
- 병렬 구조의 전기적 타당성은 AEDT import smoke test 이후 EM pipeline에서 별도 비교 실험으로 검증한다.

## 검증 계획

- `build123d` smoke
  - 단순 solid를 STEP로 export한다.
  - OCP CAD Viewer에서 생성 형상을 확인한다.
  - volume과 bounding box를 출력해 geometry sanity check를 남긴다.

- AEDT import smoke
  - headless PyAEDT session에서 STEP를 import한다.
  - import된 object 목록과 bounding box를 fail-fast로 확인한다.
  - PyAEDT API가 `False`를 반환하면 즉시 raise한다.

- type1 partial reproduction
  - 기존 type1 코일 중 하나를 `build123d`로 재현한다.
  - trace/gap, 외곽 치수, terminal 후보 위치, exported artifact 경로를 비교한다.
  - dataset/repro snapshot의 deterministic contract가 깨지지 않는지 확인한다.

## 보류 항목

- 새 코일 상세 형상은 아직 결정하지 않는다.
- 새 TOML path와 spec version bump 여부는 아직 결정하지 않는다.
- 병렬 코일의 전기적 연결 방식은 아직 결정하지 않는다.
- AEDT GUI validation은 이 문서의 기본 검증 범위에 포함하지 않는다.
- 기존 PyAEDT geometry builder 제거 시점은 AEDT import smoke test와 partial type1 reproduction 결과를 본 뒤 결정한다.

## 0.2.22 완료 기준

- 이 문서가 0.2.22 전환 방향을 기록한다.
- runtime behavior는 변경하지 않는다.
- TOML spec과 dataset/repro artifact 계약은 변경하지 않는다.
- 다음 구현 작업은 단순 `build123d` artifact 생성, AEDT headless import smoke test, type1 일부 코일 재현 순서로 진행한다.
