# Phase 6 - Coil-in-Region Constraints and Enforcement

## Goal
Phase 5의 max/actual 경계를 사용해 코일이 지정 영역 내부에 들어가도록
검증 및 강제 로직을 도입한다.

## Summary
- 대상 제약:
  - TX 코일(또는 코일 그룹) ⊂ `tx_region_vertical` 또는 `tx_region_dd` (목적별)
  - RX 코일(또는 코일 그룹) ⊂ `rx_region_actual`
- 실패 시 명확한 위반 리포트 제공(축/거리/객체명).

## In Scope
- 코일 bbox/endpoint 기반 포함성 검사.
- 필요 시 배치 보정(clamp 또는 초기 배치 단계 조정) 정책 구현.
- metadata에 constraint 결과 저장.
- 실패 모드 표준화(ValueError/RuntimeError 경계 명확화).

## Out of Scope
- 유나이트/직렬 링크 실제 수행.
- 최적화 기반 자동 배치(탐색/solver).
- 전자기 성능 목표 기반 multi-objective tuning.

## Constraint Contract
- 검사 단위:
  - 최소 단위는 coil instance.
  - group 단위 집계는 부가 메타데이터로 제공.
- 허용오차:
  - 기본 `tol_mm` 도입(예: 1e-6).
- 위반 리포트:
  - `object_name`, `region_kind`, `axis`, `overflow_mm`.

## Implementation Steps
1. region bbox 추출 유틸 작성(max/actual 구분).
2. 코일 bbox 계산과 좌표계 정합(월드 좌표 고정).
3. 포함성 검사기 구현.
4. 보정 정책 연결:
   - 우선: fail-fast only
   - 옵션: clamp-on-build (후속 토글)
5. metadata 확장:
   - `constraints_ok`, `violations[]`, `applied_adjustments[]`.
6. 콘솔 로그 요약 추가.

## Testing
- 정상 케이스:
  - 모든 코일이 영역 내부.
- 실패 케이스:
  - X/Y/Z 각각 초과 케이스.
  - RX 두께 방향(+X) 초과 케이스.
- 경계 케이스:
  - 정확히 경계에 접하는 경우 허용.
  - tol 내 오차 허용.
- 회귀:
  - 기존 deterministic/hash 계약 유지.

## Risks and Mitigation
- 리스크: 회전/변환 적용 시 bbox 판단 오차.
- 대응: 우선 axis-aligned 계약에서 시작, 회전 확장은 별도 단계로 분리.
- 리스크: 과도한 자동 보정으로 의도치 않은 배치.
- 대응: 기본값 fail-fast, 보정은 명시 옵션일 때만 수행.

## Exit Criteria
- 제약 위반 시 즉시/명확히 실패하고 원인 재현 가능.
- 정상 케이스에서 metadata에 제약 통과 근거가 기록됨.
- 후속 유나이트/연결 단계가 제약 결과를 신뢰 가능.
