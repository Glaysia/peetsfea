---
title: peetsfea
created: 2026-04-17 @ 09:09
updated: 2026-04-19 @ 15:07
tags:
  - governance
---

# peetsfea

peetsfea는 TOML 명세에서 HFSS(AEDT) 설계를 결정적으로 생성하는 Python 프로젝트입니다.

핵심 원칙: 같은 명세 + 같은 시드 = 같은 결과.

영문 문서는 [README.en.md](README.en.md)를 참고하세요.

릴리스 노트는 `release-notes/` 아래에서 버전과 언어별로 관리합니다.

## 프로젝트 목표
- 단일 TOML 명세 계약에서 HFSS 설계 생성을 표준화합니다.
- 같은 명세/버전/시드에 대해 재현 가능한 설계 생성을 보존합니다.
- 단일 설계 생성과 데이터셋 생성을 같은 계약 인터페이스에 둡니다.

## 현재 문서 기준선
- 현재 문서 기준선은 `0.2.25.1`입니다.
- 이 README는 공개 요약입니다. 현재 설계 노트는 `sdd/` 아래에 있고, 활성 build123d/AEDT 가져오기 계획은 `PLANS/` 아래에 있습니다.
- 구현 규칙은 [AGENTS.md](AGENTS.md)를 참고하세요. 현재 build123d/AEDT 가져오기 계획은 [PLANS/V0_2_22_BUILD123D_AEDT_IMPORT_PLAN.md](PLANS/V0_2_22_BUILD123D_AEDT_IMPORT_PLAN.md)를 참고하세요.

## 이 프로젝트가 보장하려는 것
- 활성 입력: type2 작성용 명세(`examples/type2_fixed.toml`)
- 활성 프로세스: type2 STEP 작성, headless HFSS 가져오기/setup-ready 검증, 선택적 EM solve/report export 경로
- legacy type1 경로는 명시적인 legacy entrypoint와 legacy 테스트/문서 아래에만 유지합니다.
- 출력: HFSS 설계 출력과 스냅샷 데이터(`.aedt`, `.repro.toml`, `.dataset.toml`, `.source.toml`)
- `repro.toml`: 실현된 설계의 정확한 replay artifact
- `dataset.toml`: 최종 설계에 영향을 주는 canonical sampled-owner 좌표의 정확한 ledger artifact

## 빠른 시작
1. Python 3.12와 AEDT runtime을 준비합니다.
2. 프로젝트 가상 환경을 사용합니다.
3. `run/`에서 테스트를 실행합니다.

```bash
cd run
../.venv/bin/pytest -q ../tests
```

활성 기본 실행은 `entry/` 아래의 type2 STEP export/import entrypoint를 통해 type2 중심으로 동작합니다. Frozen type1 batch flow는 `entry/legacy/type1/` 아래의 명시적인 legacy entrypoint를 통해서만 사용할 수 있습니다.

## 개발
프로젝트 가상 환경은 `.venv`를 사용합니다. 별도 작업이 `run/`을 작업 디렉터리로 지정하지 않는 한, 저장소 작업은 workspace root에서 실행합니다.

`src/` 아래의 repository runtime code는 assert 기반이며 fail-fast 설계입니다. `python -O`로 프로젝트를 실행하지 마세요. optimized mode는 필수 assertion을 제거하며 import/runtime에서 거부됩니다.

`src/` 전체에서 nullable runtime state와 fallback attribute/mapping access는 금지됩니다. 필수 값은 default로 대체하지 말고 명시적으로 assert한 뒤 bind해야 합니다.

`type1`은 frozen legacy입니다. active/default surface는 `type2`만 다루며, `type1` 관련 entry/test/doc/example은 legacy 경로에서만 opt-in으로 사용합니다.

## 디버그 실행
`.vscode/tasks.json`의 VS Code debug task는 실행 전에 프로젝트를 editable mode로 설치합니다. 이 파일은 그 단계에서 `pyproject.toml`에 선언된 package metadata가 유효한 readme target을 갖도록 존재합니다.

## 핵심 산출물
- Zip export는 임시로 비활성화되어 있습니다.
- 실행 결과는 여전히 다음 네 payload를 스냅샷으로 유지합니다.
  - `<design_id>.aedt`
  - `<design_id>.repro.toml`
  - `<design_id>.dataset.toml`
  - `<design_id>.source.toml`
- `manifest_<design_id>.json`과 `geometry_metadata_<design_id>.json`은 기본적으로 비활성화되어 있으며 선택 사항입니다.

## 0.2.25.1의 주요 계약
- Active type2 기본 경로는 TxRx example surface와 RxOnly setup-ready backend의 조합입니다.
- Active type2는 RX modeled geometry, RX mesh, RX lumped port, RX report variables만 setup-ready 대상으로 삼습니다.
- 송신 형상, 송신 포트, 송신 출력 변수는 active type2 계약에서 제거되었습니다.
- `tx_region`은 향후 송신 형상을 배치하기 위한 non-modeled guide로만 유지됩니다.
- `tv_aluminum_plate`는 `tv`의 `+X` face에 놓이는 optional finite-conductivity HFSS sheet입니다. STEP solid로 export하지 않습니다.
- `modeled_objects.tv_aluminum_plate.sheet_present`는 canonical presence owner이며, active sweep dimension count는 14입니다.
- Sheet가 present일 때 setup-ready는 `aluminum`, `use_thickness=True`, `thickness=0.04mm`, boundary name `bc_tv_aluminum_plate` 계약을 사용합니다.
- Sampling ownership은 canonical owner를 통해서만 관리합니다.
- Alias/derived path는 독립 sampled dimension으로 계산하지 않습니다.
- `dataset.toml`과 `repro.toml`은 역할이 다르며, replay safety는 두 artifact의 대응 관계로 정의합니다.
- Adaptive default는 `percent_refinement=22`, `maximum_passes=10`, `minimum_passes=8`, `minimum_converged_passes=10`, `max_delta_s=0.007`로 표준화되어 있습니다.

## Legacy type1 참고 문서
- 한글 개요: [docs/legacy/type1.md](docs/legacy/type1.md)
- 영문 개요: [docs/legacy/type1.en.md](docs/legacy/type1.en.md)

## 호환성 정책
- 장기 backward compatibility는 보장하지 않습니다.
- Major/minor release는 spec path, default, artifact contract를 변경할 수 있습니다.

## 릴리스 이력
공개 이력을 간결하게 유지하기 위해 release work는 `main`에 squash될 수 있습니다. 이 경우 topic branch는 상세 commit history를 유지할 수 있고, 이후 `main`이 다시 진행된 뒤 일반 merge로 `main`에 동기화할 수 있습니다.

## 저작 및 면책
- 코드 생성: 이 저장소의 코드는 GPT-5.x Codex가 100% 생성했습니다.
- 책임: 코드/문서 사용으로 발생하는 문제에 대해 어떠한 보증이나 책임도 제공하지 않습니다.
- 영문 문서 고지: `README.en.md`를 포함한 영문 문서는 AI가 생성했으며 수동 검토되지 않았습니다. 정확성/완전성/적합성은 보장하지 않습니다.

## 기여
아이디어, 버그 보고, spec 제안은 Issues를 사용하세요.
