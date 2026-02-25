# PHASE5 - 코일 직렬연결(브리지) + TX/RX Unite

## 목표
- 가장 어려운 단계: 코일들을 실제 구리 리드/브리지로 직렬연결해 TX 1개, RX 1개 도체로 만든다.

## 범위
- geometry 입력 규약:
  - 공통 `outer_x/outer_y` 참조 금지
  - 그룹별 `outer_x/outer_y` 참조 의무
  - bridge/unite 시작 전 `group_outer_mapping_passed` 선검증
- 공용화 규약:
  - series bridge/unite 로직을 type-agnostic helper로 분해
  - type1은 helper 호출자로 축소하고 type2도 동일 helper를 사용
- 체인 순서:
  - TX: `tx_dd + tx_vertical` deterministic 정렬
  - RX: `rx_dd` deterministic 정렬
- 인접 코일 연결:
  - 리드(stub) 2개 + 2D 직사각 브리지 생성
- Unite:
  - TX -> `coil_tx_united_<design_id>`
  - RX -> `coil_rx_united_<design_id>`
- 메타데이터:
  - `series_chain`, `unite_groups`(실제 결과명 기준)
  - 공용 `EmPipelineResult.series`와 1:1 대응

## 실패 규약
- zero-length/self-intersection/region 이탈/unite 실패 시 즉시 hard fail
- `group_outer_mapping_passed` 실패 시 브리지 단계 진입 금지
