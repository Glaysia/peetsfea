# V0.2.11-02 Ferrite Geometry And Metadata

## 상태/목적
- 상태: Planned
- 목적: 전역 ferrite flag가 geometry, metadata, EM 준비 객체에 어떻게 반영되는지 구현 단위로 고정한다.
- 이번 문서는 geometry 의사결정만 정리하며 실제 모델 생성 코드는 아직 변경하지 않는다.
- ferrite spec path와 adaptive defaults는 `01`, replay/dataset contract는 `00C`를 참조한다.

## Geometry 배치 의도
- RX ferrite는 RX 영역 뒤쪽에 붙는 판으로 정의한다.
- TX ferrite는 TX 영역 아래쪽에 붙는 판으로 정의한다.
- `ferrite.present = 1`일 때만 RX/TX 두 판을 함께 생성한다.
- `ferrite.present = 0`이면 RX/TX 두 판을 모두 생성하지 않는다.
- 둘 중 하나만 생성되는 모드는 비지원이다.
- ferrite는 단순 scene reference가 아니라 실제 해석 대상 model object로 취급한다.

## Metadata/EM 반영 계약
- geometry metadata에는 RX/TX ferrite object가 존재 여부와 함께 반영되어야 한다.
- scene object 목록에는 ferrite를 식별 가능한 kind로 기록해야 한다.
- EM 준비 객체에는 ferrite 관련 object 집합이 별도로 식별되어야 한다.
- major grouping에서도 ferrite 객체를 별도 그룹으로 다룰 수 있어야 한다.
- non-model scene box와 ferrite model object는 문서상에서 명확히 구분한다.

## 구현 메모
- 영향 subsystem은 아래로 고정한다.
  - `scene_objects`
  - geometry build state
  - geometry metadata
  - EM ready objects
  - grouping
- 이번 문서에서는 구체 좌표식이나 코드 diff 대신 배치 의도와 반영 계약만 고정한다.

## 비범위
- ferrite TOML path와 sampling ownership
- adaptive policy 기본값
- dataset/repro/uniform seedset contract

## 수용 기준
- RX ferrite와 TX ferrite의 배치 방향이 문서만 읽어도 해석 가능하다.
- ferrite가 model object라는 점이 명시되어 있다.
- metadata와 EM 준비 경로에서 ferrite를 어떻게 취급할지 누락 없이 적혀 있다.
- 전역 flag가 geometry/metadata에서 RX/TX를 함께 제어한다는 점이 명확하다.
