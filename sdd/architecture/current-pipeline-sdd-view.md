---
title: Current Pipeline SDD View
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - legacy_type1
  - sdd
---

# Current Pipeline SDD View

이 문서는 frozen legacy type1 파이프라인의 SDD 관점 요약이다. active default path는 더 이상 이 문서를 기준으로 하지 않는다. 자세한 legacy 분석은 [[docs/legacy/current-pipeline-type1]]를 보고, active path는 [[docs/current-pipeline]]를 본다.

## Boundary
- 입력 SSOT는 TOML spec이다.
- legacy 샘플링 entry는 [[sdd/code/entry/legacy/type1/sample.py]]가 대표 예시다.
- TOML 로딩과 최소 shape 검증은 [[sdd/code/src/peetsfea/spec/loader.py]]가 담당한다.
- 샘플링 registry 계약은 [[sdd/code/tests/spec_resolver/test_sampling_registry.py]] 같은 테스트가 방어한다.

## Flow
1. `entry/legacy/type1/sample.py`가 batch profile을 계산한다.
2. seed selection과 sample artifact generation을 호출해 frozen TOML과 `manifest.json`을 만든다.
3. build entry가 manifest replay를 통해 geometry build와 EM pipeline으로 넘긴다.
4. selection, geometry, EM 단계는 fail-fast 계약을 지키며 중간 fallback 없이 멈춘다.

## Structural invariants
- TOML spec은 여전히 기능 입력의 SSOT다.
- SDD는 코드 경계, ownership, fail-fast 의도의 SSOT다.
- 샘플링과 리플레이 ownership은 한 canonical owner만 가져야 한다.
- build/run 실패는 기본적으로 즉시 멈춰야 한다.

## Related notes
- 구조도: [[sdd/diagrams/sample-build-flow]]
- 예시 코드 노트:
  - [[sdd/code/entry/legacy/type1/sample.py]]
  - [[sdd/code/src/peetsfea/spec/loader.py]]
  - [[sdd/code/tests/spec_resolver/test_sampling_registry.py]]
