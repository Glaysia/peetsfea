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
- 버전: `0.3.2`
- 활성 입력: [examples/minimal_step_two_port.toml](examples/minimal_step_two_port.toml)
- TOML surface: `[design]`과 `[[non_model_objects]]`만 허용
- STEP surface: authored non-model box들과 고정 Tx/Rx port cell
- EM surface: Tx 포트 1개, Rx 포트 1개, copper pad mesh, radiation boundary, `Setup1`, `Sweep`, `Output Variables Table1`
- SSW debug 입력 [examples/0.3.2_fixed.toml](examples/0.3.2_fixed.toml)과 [examples/0.3.2_sweep.toml](examples/0.3.2_sweep.toml)은 0.2.25 type2와 같은 `[constraints]` / `[[constraints.rules]]` 표면을 쓰며, enabled SSW coil은 `gcd(turn_n_int, twist_factor) == 1`이어야 하고 RX SSW가 enabled일 때 RX `turn_n_int`는 1보다 커야 합니다. 0.3.1부터 TX/RX `void_profile`은 scaled void profile `1`로 고정합니다. 0.3.2 sweep SSOT는 [examples/0.3.2_sweep.toml](examples/0.3.2_sweep.toml)이며 `validate_sweep_toml_text`의 기준 design space입니다.
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

설계 공간 안에서 seed 범위로 랜덤 SSW STEP 파일을 생성하고, 그중 한 seed를 OCP로 봅니다. `entry/sample.py`가 유일한 entry 스크립트입니다.

```bash
cd run
# seed 0..9에 대해 STEP 생성 후 seed 0을 OCP에 표시
../.venv/bin/python ../entry/sample.py --seed-start 0 --seed-end 9
# 특정 seed만 OCP로 보기
../.venv/bin/python ../entry/sample.py --seed-start 0 --seed-end 9 --view-seed 3
# 병렬(워커 10개) 생성, 뷰어 없이
../.venv/bin/python ../entry/sample.py --seed-start 0 --seed-end 99 --jobs 10 --no-view
```

`--jobs N`은 seed별 생성을 N개 프로세스로 병렬 처리합니다(각 seed는 독립 디렉토리라 안전하며 결과는 결정적). `--debug`는 소스 상단 `DEBUG_*` 상수로 인자를 제어합니다.

Headless AEDT setup/solve/report 경로는 패키지 공개 API(`peetsfea.run_ssw_random_sample_reports_from_toml_text`)와 `tests/backend_em`의 headless AEDT 통합 테스트로 실행합니다. 기존 minimal `entry/sample.py`·`entry/build.py` 진입점은 제거했습니다.

## 산출물
`entry/sample.py`의 기본 출력 위치는 gitignored `run/ssw_step_samples/seed_<NNNNN>/`이며 seed마다 다음을 생성합니다.

- `<design_id>.toml` (sampled fixed point)
- `ssw_scene.step`
- `ssw_step_ledger.json`
- `coil_making_token.toml`

SSW headless AEDT 솔브 산출물(`<design_id>.aedt`, report CSV 등)은 공개 API 결과의 `output_dir` 아래에 생성됩니다.

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

## 0.3.2 runner 통합 API
peetsfea-runner가 의존하는 공개 표면입니다. peetsfea는 ansysedt를 직접 기동/종료하거나 라이선스를 관리하지 않습니다.

- `peetsfea.__version__ == "0.3.2"`, 패키지에 `py.typed` 동봉(공개 API strict 타입체킹).
- `peetsfea.validate_sweep_toml_text(sweep_text)` — sweep TOML 전체 텍스트의 모든 swept range가 기준 sweep([examples/0.3.2_sweep.toml](examples/0.3.2_sweep.toml)) design space(상하한 + 정수/실수 플래그 + count>0) 이내인지 검사하고, 벗어나면 `PeetsfeaStageError`를 raise합니다.
- `peetsfea.sample_fixed_candidates_from_toml_text(sweep_text, count, seed) -> list[str]` — sweep 1건을 fixed candidate `count`개 TOML 텍스트로 결정론적(동일 seed=동일 결과) 확장합니다. scratch는 환경의 `TMPDIR`을 따릅니다(`/tmp`·`/dev/shm` 직접 사용 금지).
- `peetsfea.run_ssw_random_sample_reports_from_toml_text(candidate_toml_text, *, output_dir, seed, mode, grpc_port, aedt_pid=None)` — runner가 빌려준 warm ansysedt에 `grpc_port`(우선) 또는 `aedt_pid`로 attach하여 빌드·solve·report합니다. 자체 기동/종료를 하지 않고, 끝나면 프로젝트만 닫고 AEDT는 살린 채 반환합니다. attach 불가 시 `PeetsfeaStageError(stage="attach")`를 raise하여 runner가 해당 AEDT를 재활용하도록 합니다.
- solve는 내부 watchdog로 `solve_hard_abort_seconds`(기본 3600s=60분)에 도달하면 `stop_simulations(clean_stop=True)`로 hard-abort하고 마지막 완료 패스 리포트를 남깁니다. 결과의 `solve_outcome`에 `completed`/`hard_aborted`가 담깁니다.
- 모든 실패는 구조화 예외 `peetsfea.PeetsfeaStageError`(`stage`/`error_type`/`message`, `RuntimeError` 하위)로 보고됩니다.

## 호환성 정책
장기 backward compatibility는 보장하지 않습니다. Minor release도 spec path, artifact contract, runtime entrypoint를 변경할 수 있습니다.
