# V0.2.11-03 Tests And Acceptance

## 상태/목적
- 상태: Planned
- 목적: `0.2.11` 구현 완료 판정을 위한 테스트 범위와 acceptance checklist를 고정한다.
- 이번 문서는 테스트 계획서이며, 실제 테스트 추가/수정은 아직 수행하지 않는다.
- 이 문서는 `00A~02` 계약을 검증하는 문서이며, 새로운 설계 규칙 자체를 다시 정의하지 않는다.

## 테스트 분류
- validation 테스트
  - `spec_version 0.2.11` 기대값
  - `ferrite.present` 신규 key 인식
  - adaptive 기본값 `20/20/0.007` 기대값
- determinism 테스트
  - `ferrite.present` 샘플링이 seed 기준으로 재현 가능해야 한다.
- geometry/metadata 테스트
  - ferrite on일 때 RX/TX ferrite object가 모두 존재해야 한다.
  - ferrite off일 때 RX/TX ferrite object가 모두 없어야 한다.
  - ferrite 위치/크기와 metadata 반영이 기대 계약과 일치해야 한다.
- EM policy 테스트
  - setup payload에 `percent_refinement=20`, `maximum_passes=20`, `max_delta_s=0.007`이 반영되어야 한다.

## Acceptance Criteria
- 문서, 코드, 테스트가 같은 용어를 사용한다.
- 전역 ferrite semantics가 validation과 geometry 테스트 양쪽에서 동일하게 검증된다.
- adaptive policy 기본값 3개가 parser, manifest, default policy, EM setup 기대값에 일관되게 반영된다.
- ferrite on/off에 따라 RX/TX가 동시에 생기거나 동시에 사라지는 계약이 테스트로 고정된다.
- sampling ownership, replay safety, dataset ledger 계약은 `00A~00C` 기준으로 검증된다.

## 완료 정의
- 필요한 테스트 추가 범위를 이 문서만 읽고 누락 없이 나열할 수 있다.
- validation, determinism, geometry/metadata, EM policy 4개 축이 모두 포함되어 있다.
- acceptance checklist가 문서-코드-테스트 동기화 관점으로 정리되어 있다.
- 이번 단계에서는 테스트를 실행하지 않는다.
