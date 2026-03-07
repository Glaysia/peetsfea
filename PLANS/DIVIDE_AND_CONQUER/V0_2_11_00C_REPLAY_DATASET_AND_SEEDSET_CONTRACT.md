# V0.2.11-00C Replay Dataset And Seedset Contract

## 상태/목적
- 상태: Planned
- 목적: replay safety, dataset ledger, uniform seedset 차원 벡터 계약을 `0.2.11` public contract로 고정한다.
- 이번 문서는 외부 산출물과 replay 계약을 정의하며 실제 코드/문서 갱신은 아직 수행하지 않는다.
- sampling ownership 자체는 `00A`, selection 내부 구조는 `00B`에서 정의한다.

## Snapshot 계약
- `dataset.toml`의 의미는 `exact sampled-coordinate ledger`로 고정한다.
- 포함 대상은 최종 설계에 영향을 주는 모든 독립 sampled DOF다.
- 제외 대상은 derived alias, normalized-away field, fixed field다.
- `repro.toml`은 계속 실행 가능한 frozen TOML 역할을 유지한다.
- exact replay의 기준 산출물은 `repro.toml`이다.

## Replay/Export 규칙
- repro freezing은 tree heuristic이 아니라 ledger owner map으로 수행한다.
- dataset export는 registry canonical owner path만 사용한다.
- derived alias는 dataset 차원으로 세지지 않는다.
- dataset path set과 repro frozen owner set은 1:1 대응해야 한다.
- 숫자 차원 수는 고정 계약으로 박지 않는다.
- example spec의 독립 차원 수는 registry scan 결과로 설명하고, 값이 변하면 docs/tests도 함께 갱신한다.

## Uniform Seedset 규칙
- `uniform_seedset`은 canonical key의 고정 순서만 사용한다.
- hidden dimension 추가 없이 coverage metric이 유지되어야 한다.
- context key 정렬 같은 우발적 구현 상세에는 의존하지 않는다.

## 비범위
- sampling registry owner 분류 방식 자체
- resolver/pipeline 내부 리팩토링 구조
- ferrite spec path, geometry, adaptive defaults

## 문서/공개 계약 갱신 대상
- `README.md`
- `docs/type1.md`
- `docs/type1.en.md`
- 필요 시 영문 README도 같은 계약으로 동기화한다.
- 문서에는 dataset이 count-array 계열까지 포함한다는 점과 derived alias는 차원으로 세지지 않는다는 점을 명시한다.

## 테스트 축
- dataset coverage
- replay equivalence
- canonical-order uniform-seedset regression
- example spec dimension count는 registry scan 결과와 dataset/export 일치 여부만 검증하고 고정 상수는 사용하지 않는다.

## 수용 기준
- dataset과 repro의 역할 구분이 문서만 읽어도 명확하다.
- replay safety가 ledger owner 기준으로 정의되어 있다.
- uniform seedset이 canonical key 순서에만 의존해야 한다는 점이 명시되어 있다.
- 차원 수는 회귀 관찰값일 뿐 고정 계약이 아니라는 점이 분명하다.
