# PHASE9 - 최종 Validation Gate + 수용 테스트

## 목표
- 전체 파이프라인을 hard fail validation gate로 묶고 릴리즈 수용 기준을 확정한다.

## validation 체크리스트
- selection ratio 제약 통과
- `no_hidden_derivation_passed` 검증 통과 (sampled 변수와 내부 설계변수의 암묵 다중 파생 없음)
- `no_max_override_passed` 검증 통과 (`rx_region_thickness_mm` 포함)
- `group_outer_mapping_passed` 검증 통과
- 공용 EM 파이프라인 계약 충족 (`em_ready_objects`, `em_endpoints`, `em_context`)
- 그룹 생성 완료
- TX/RX 직렬 체인 연결성
- TX/RX unite 결과 존재
- FR4 subtract 성공
- radiation region/boundary 존재
- TX/RX lumped port 존재
- setup/sweep 존재
- 결과 템플릿 존재
- 공용 `EmPipelineResult` 필수 필드 존재

## 테스트 축
1. ratio -> mm 파생식 정확성
2. ratio 극단값 경계(pass/fail)
3. 비활성 그룹 제약 skip
4. 그룹별 `outer_x/outer_y`가 각 그룹 형상에 독립 반영되는지 검증
5. 공통 `outer_x/outer_y` 또는 제거된 spacing(mm) 경로 사용 시 명시적 오류 검증
6. sampled `rx_region_thickness_mm`가 강제 max 오버라이드 없이 유지되는지 검증
7. replay 검증: sampled run -> frozen TOML 생성 -> rerun 시 형상 동일
8. JSON replay 회귀: manifest 기반 생성 결과와 형상 동일
9. 구버전 `spec_version` 입력 시 명시적 버전 오류 검증
10. 브리지 연결 후 TX/RX 1개 unite 보장
11. subtract/port/setup/result 존재성
12. validation hard fail 동작
13. 통합(type2-ready mock): 공용 EM 파이프라인 단독 실행 성공
14. type1/type2 공통 acceptance 체크리스트 동일 기준 통과

## 수용 기준
- 위 체크 중 하나라도 실패하면 실행 실패
- 실패 로그에 단계/객체/원인 포함
- 관련 테스트가 CI에서 안정 통과
