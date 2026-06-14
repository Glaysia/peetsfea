---
title: peetsfea
created: 2026-04-17 @ 09:09
updated: 2026-06-14 @ 00:00
tags:
  - governance
---

# peetsfea

peetsfea는 TOML 명세에서 HFSS(AEDT) 설계를 결정적으로 생성하는 Python 프로젝트입니다.

0.3.0 기준선은 누적된 기존 형상 생성 코드를 제거하고, non-model TOML + 최소 STEP + 두 금속 포트 + headless EM setup/solve/report 경로만 활성 계약으로 둡니다.

영문 문서는 [README.en.md](README.en.md)를 참고하세요.

## 현재 계약
- 버전: `0.3.0`
- 활성 입력: [examples/minimal_step_two_port.toml](examples/minimal_step_two_port.toml)
- TOML surface: `[design]`과 `[[non_model_objects]]`만 허용
- STEP surface: authored non-model box들과 고정 Tx/Rx port cell
- EM surface: Tx 포트 1개, Rx 포트 1개, copper pad mesh, radiation boundary, `Setup1`, `Sweep`, `Output Variables Table1`
- SSW debug 입력 [examples/0.3.0_fixed.toml](examples/0.3.0_fixed.toml)과 [examples/0.3.0_sweep.toml](examples/0.3.0_sweep.toml)은 0.2.25 type2와 같은 `[constraints]` / `[[constraints.rules]]` 표면을 쓰며, enabled SSW coil은 `gcd(turn_n_int, twist_factor) == 1`이어야 하고 RX SSW가 enabled일 때 RX `turn_n_int`는 1보다 커야 합니다.
- SSW debug의 `tx_under_coil`은 TX main coil과 별도인 두 번째 TX coil이며, `tx_region_max`의 global X-min 면 바깥에 붙는 YZ 평면 normal spiral입니다.
- SSW debug MULL ferrite 위치는 TX Z축 `ferrite.tx_mull_position_ratio`와 RX X축 `ferrite.rx_mull_position_ratio`로 따로 제어합니다.
- 기본 실행과 AEDT/PyAEDT 변경 검증은 headless이며 PyAEDT `False` return은 즉시 raise합니다.
- AEDT/PyAEDT 관련 코드를 수정한 agent는 실제 headless AEDT 검증을 직접 실행해야 하며, 실행 불가 시 완료로 보고하지 않습니다.

## 실행
테스트는 `run/`에서 실행합니다.

```bash
cd run
../.venv/bin/pytest -q ../tests
../.venv/bin/pyright ../src ../entry ../tests
```

최소 STEP 샘플 artifact를 생성합니다.

```bash
cd run
../.venv/bin/python ../entry/sample.py
```

Headless AEDT setup-ready 프로젝트를 생성합니다.

```bash
cd run
../.venv/bin/python ../entry/build.py
```

Solve와 CSV report export까지 실행합니다.

```bash
cd run
../.venv/bin/python ../entry/build.py --solve
```

## 산출물
기본 출력 위치는 `run/sampled/minimal/<design_id>/`입니다.

- `sampled.toml`
- `<design_id>.source.toml`
- `<design_id>.repro.toml`
- `<design_id>.dataset.toml`
- `minimal_scene.step`
- `minimal_step_ledger.json`
- `<design_id>.aedt`
- `minimal_imported_ledger.json`
- `Output_Variables_Table1.csv` when `--solve` is used

## 규칙
- `python -O`는 지원하지 않습니다. assertion은 runtime contract의 일부입니다.
- `src/` runtime state는 nullable/fallback 기반으로 다루지 않습니다.
- GUI AEDT 확인은 보조 진단일 뿐이며, headless AEDT 검증을 대체하지 않습니다.
- 기존 type2, rect-void, legacy geometry path는 0.3.0 활성/legacy 구현으로 유지하지 않습니다.

## 문서
- 목표: [GOAL.md](GOAL.md)
- 현재 파이프라인: [docs/current-pipeline.md](docs/current-pipeline.md)
- Palace 세컨드 백엔드 로드맵: [docs/palace-second-backend-roadmap.md](docs/palace-second-backend-roadmap.md)
- 0.3.0 계획: [sdd/plans/0.3.0-minimal-step-two-port-reset.md](sdd/plans/0.3.0-minimal-step-two-port-reset.md)
- 작업 규칙: [AGENTS.md](AGENTS.md)

## 호환성 정책
장기 backward compatibility는 보장하지 않습니다. Minor release도 spec path, artifact contract, runtime entrypoint를 변경할 수 있습니다.
