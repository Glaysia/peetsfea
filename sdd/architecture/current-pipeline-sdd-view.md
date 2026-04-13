# Current Pipeline SDD View

이 문서는 현재 파이프라인의 SDD 관점 요약이다. 자세한 분석은 [[docs/current-pipeline]]를 보고, 현재 도입 계획은 [[sdd/plans/0.2.22-sdd-adoption]]를 본다.

## Boundary
- 입력 SSOT는 TOML spec이다.
- 샘플링 entry는 [[sdd/code/entry/sample.py]]가 대표 예시다.
- TOML 로딩과 최소 shape 검증은 [[sdd/code/src/peetsfea/spec/loader.py]]가 담당한다.
- 샘플링 registry 계약은 [[sdd/code/tests/spec_resolver/test_sampling_registry.py]] 같은 테스트가 방어한다.

## Flow
1. `entry/sample.py`가 batch profile을 계산한다.
2. seed selection과 sample artifact generation을 호출해 frozen TOML과 `manifest.json`을 만든다.
3. build entry가 manifest replay를 통해 geometry build와 EM pipeline으로 넘긴다.
4. selection, geometry, EM 단계는 fail-fast 계약을 지키며 중간 fallback 없이 멈춘다.

## Structural invariants
- TOML spec은 여전히 기능 입력의 SSOT다.
- SDD는 코드 경계, ownership, fail-fast 의도의 SSOT다.
- 샘플링과 리플레이 ownership은 한 canonical owner만 가져야 한다.
- build/run 실패는 기본적으로 즉시 멈춰야 한다.

## Related notes
- 허브: [[sdd/index]]
- 코드 허브: [[sdd/code/index]]
- 구조도: [[sdd/diagrams/sample-build-flow]]
- 구조 문서: [[sdd/structure/sdd-vault-layout]]
- 예시 코드 노트:
  - [[sdd/code/entry/sample.py]]
  - [[sdd/code/src/peetsfea/spec/loader.py]]
  - [[sdd/code/tests/spec_resolver/test_sampling_registry.py]]
