# peetsfea

TOML 스펙을 입력으로 받아 HFSS(AEDT)용 설계를 결정론적으로 생성하는 Python 프로젝트다.  
핵심 목표는 "같은 스펙 + 같은 시드면 같은 결과"다.

영문 문서는 [README.en.md](README.en.md)를 참고한다.
릴리즈 노트는 `release-notes/` 폴더에서 버전별/언어별로 관리한다.

## 프로젝트 목표
- TOML 스펙 하나로 HFSS 설계 생성 과정을 표준화한다.
- 동일 스펙/버전/시드에서 같은 설계를 재현 가능하게 유지한다.
- 단일 설계 생성과 데이터셋 생성이 같은 계약 위에서 동작하도록 유지한다.

## 현재 문서 기준
- 현재 문서 정리의 기준 릴리즈는 `0.2.11` 계획이다.
- 공개 요약은 이 README가 담당하고, 세부 설계는 `PLANS/` 문서가 담당한다.
- 구현 규칙은 [AGENTS.md](AGENTS.md), 장기 원칙은 [PLANS/LONGTERM_PLAN.md](PLANS/LONGTERM_PLAN.md), `0.2.11` 인덱스는 [PLANS/V0_2_11.md](PLANS/V0_2_11.md) 를 참고한다.

## 이 프로젝트가 보장하려는 것
- 입력: TOML 스펙(`examples/type1.toml`)
- 처리: 스펙 검증 + deterministic selection + HFSS 설계 생성
- 출력: HFSS 설계와 스냅샷 데이터(`.aedt`, `.repro.toml`, `.dataset.toml`, `.source.toml`)
- `repro.toml`: realized design을 다시 실행할 수 있는 exact replay artifact
- `dataset.toml`: 최종 설계에 영향을 주는 sampled coordinate를 추적하는 ledger artifact

## 빠른 시작
1. Python 3.12와 AEDT 환경을 준비한다.
2. 가상환경을 사용한다.
3. `run/` 기준으로 테스트를 실행한다.

```bash
cd run
../.venv/bin/pytest -q ../tests
```

기본 실행 예시는 `run.py`, 기본 스펙은 `examples/type1.toml`을 사용한다.

## 핵심 산출물
- zip 산출물은 현재 임시 비활성화 상태다.
- 실행 결과에서는 아래 4개 payload가 `RunResult` 스냅샷으로 유지된다.
  - `<design_id>.aedt`
  - `<design_id>.repro.toml`
  - `<design_id>.dataset.toml`
  - `<design_id>.source.toml`
- `manifest_<design_id>.json`, `geometry_metadata_<design_id>.json`은 기본 비활성이다(옵션으로만 생성).

## 0.2.11에서 정리하는 큰 계약
- sampling ownership은 canonical owner 기준으로만 관리한다.
- alias/derived path는 독립 sampled dimension으로 세지지 않는다.
- `dataset.toml`과 `repro.toml`은 서로 다른 역할을 가지며, replay safety는 둘의 대응 관계로 관리한다.
- 세부 설계는 아래 문서로 분리되어 있다.
  - [PLANS/V0_2_11.md](PLANS/V0_2_11.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_00A_SAMPLING_LEDGER_AND_PREFLIGHT.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_00A_SAMPLING_LEDGER_AND_PREFLIGHT.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_00B_SELECTION_API_SIMPLIFICATION_AND_REFACTOR.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_00B_SELECTION_API_SIMPLIFICATION_AND_REFACTOR.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_00C_REPLAY_DATASET_AND_SEEDSET_CONTRACT.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_00C_REPLAY_DATASET_AND_SEEDSET_CONTRACT.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_01_SPEC_AND_POLICY.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_01_SPEC_AND_POLICY.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_02_FERRITE_GEOMETRY_AND_METADATA.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_02_FERRITE_GEOMETRY_AND_METADATA.md)
  - [PLANS/DIVIDE_AND_CONQUER/V0_2_11_03_TESTS_AND_ACCEPTANCE.md](PLANS/DIVIDE_AND_CONQUER/V0_2_11_03_TESTS_AND_ACCEPTANCE.md)

## type1 참고 문서
- 설계 개요: [docs/type1.md](docs/type1.md)
- 영문 설계 개요: [docs/type1.en.md](docs/type1.en.md)

## 호환성 정책
- 장기 하위호환을 보장하지 않는다.
- 메이저/마이너 릴리즈에서 스펙 경로, 기본 동작, 산출물 계약이 변경될 수 있다.

## Authorship & Disclaimer
- 코드 생성: 이 저장소의 코드와 문서는 100% GPT-5.x Codex가 생성했다.
- 책임 범위: 코드/문서 사용으로 발생하는 문제에 대해 작성자는 보증이나 책임을 제공하지 않는다.
- 영문 문서 고지: README를 포함한 영문 문서는 AI가 생성했으며 별도 검토를 하지 않았다. 영문 문서의 정확성/완전성/적합성은 보장하지 않는다.

## 기여
아이디어/버그 제보/스펙 제안은 Issue로 받는다.
