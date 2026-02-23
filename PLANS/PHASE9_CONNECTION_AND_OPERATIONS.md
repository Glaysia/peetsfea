# Phase 9 - Connection Builder 및 운영화

## Goal
배치/제약이 고정된 상태에서 endpoint 기반 연결기와 대량 실행 운영 루프를 완성한다.

## Summary
- endpoint metadata 기반 Unite/링크 생성
- polarity 보존 검증
- 실패 분류/관측성/배치 스윕 운영 템플릿 제공

## In Scope
- connection builder 모듈 추가
- run 파이프라인 실패 분류 표준화
- 데이터셋 운영 스크립트 및 결과 스키마 고정

## Out of Scope
- 물리 최적화 알고리즘 자체(탐색기 고도화)

## Workstreams
1. Connection Builder
- 입력: `group_endpoints`, polarity spec, mounts
- 처리: role/group 기반 unite + clearance-aware link
- 출력: net object 목록, 연결 로그

2. Experiment Operations
- 프로필/배치 sweep 템플릿 제공
- 실패 원인 분류:
  - preflight constraint
  - geometry build
  - solver/runtime

3. Observability
- manifest/geometry metadata에 연결 판정 표준 필드 추가
- batch 실행 요약 CSV/JSON 생성

## Testing
- 통합: 연결 전후 endpoint 개수/방향성 일치
- polarity 회귀: 계약 위반 시 실패
- 운영 회귀: 동일 spec+seed 재현성 유지

## Exit Criteria
- 연결 결과가 자동 검증되고 재현 가능
- 대량 실행 시 실패 분류가 자동 집계됨
- 배치 제약 위반 0건(run 유효 spec 기준)
