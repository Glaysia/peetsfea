# GOAL 1 — `pfsolver` Python 오케스트레이터 (스트림 A)

병렬 작업 둘 중 **A**. 짝: [GOAL2_forked_palace.md](GOAL2_forked_palace.md)(Palace 포크/μ 패치).
이 스트림은 **Python 오케스트레이터**를 만든다. **no-ferrite는 GOAL2의 μ 패치 없이 진행 가능**하다(아래 병렬성 참고).

## 목표
`solver/pfsolver` 독립 Python API 서브프로젝트가 동작하고, `inspect_bundle`·`mesh_bundle`·`solve_bundle`
API가 **no-ferrite 단일주파수(6.78 MHz)** 에서 Palace wrapper가 감싼 컨테이너 Palace를 호출해
2-포트 terminal Z를 산출하고 재현 가능한 manifest를 남기는 상태까지. HFSS no-ferrite numeric 기준선은
GOAL2가 채웠고, 현재 pfsolver 수치 교차검증은 conductor/air-domain 모델링 보정 전이라 FAIL로 기록한다.

## 아키텍처 (pyaedt → ansysedt 구도)
- `pfsolver` = **독립 Python API 서브프로젝트** (`solver/pfsolver`, pyright strict + pydantic), **도커 밖**.
- peetsfea-facing CLI는 만들지 않는다. peetsfea는 나중에 `pfsolver` Python API를 import/call한다.
- repo root `src/peetsfea/`에 구현하지 않는다. `solver/pfsolver/`는 `solver/palace/`와 별도 서브모듈/서브프로젝트로 개발한다.
- 역할: 번들 ingest → **gmsh(Python API)** 메시 → Palace `Driven` config(JSON) emit →
  **Palace wrapper CLI 호출**(JSON in / CSV out) → CSV→Z 후처리 → manifest.
- 컨테이너 안엔 **Palace 엔진만**(stock `palace:0.16.1`, ferrite 단계는 GOAL2 산출 `palace:0.16.1pf`). 오케스트레이터엔 C++ 없음.

## 병렬성 (GOAL2와의 경계)
- **Phase A(inspect)·B(mesh·config·dry-run)** 는 Palace solve가 필요 없다 → **GOAL2와 완전 병렬, 의존 0.**
- **Phase C(solve)** 만 Palace 이미지/래퍼가 필요 → **GOAL2의 M1(upstream-동등 빌드)** 이면 충분(μ 패치 불필요).
  no-ferrite는 upstream Palace 기능만 쓴다.
- **ferrite(복소 μ)** 만 GOAL2의 M-fork에 의존 → 이번 push 범위 밖(나중).
- 임시 unblock: GOAL2 이미지 전이라도 Phase C는 stock upstream `palace` 이미지로 개발/테스트 가능(no-ferrite라 동등).

## Palace 인터페이스 계약 (GOAL2와 합의된 경계 — 깨지면 안 됨)
- 입력: 오케스트레이터가 **Palace `Driven` config(JSON)** + **mesh(.msh)** 를 emit.
- 호출: **런타임 무관 래퍼 `palace <config.json>`** 로 부른다. 직접 `docker run`/`podman run` 하드코딩 금지.
  - 로컬 dev = `~/.local/bin/palace`(podman/docker-wrapped, pyaedt→podman-aedt 패턴). 설치: `solver/local/install-palace-local.sh`.
  - 클러스터 = enroot/pyxis(`srun --container-image=…`). 같은 계약(config in / CSV out)이라 래퍼만 다름.
  - 제어 env: `PFSOLVER_CONTAINER_RUNTIME`(podman/docker)·`PFSOLVER_PALACE_IMAGE`·`PFSOLVER_MPI_RANKS`(4)·`PFSOLVER_WORKDIR`.
  - 래퍼가 컨테이너 안에서 `mpirun -np 4 palace`(4 rank, GPU, HYPRE pool override LD_PRELOAD) 실행.
- **지금은 stock 릴리스 `palace:0.16.1`**(포크 패치 없음, no-ferrite 충분). ferrite 단계에서 `PFSOLVER_PALACE_IMAGE=palace:0.16.1pf`(GOAL2 포크)로 전환.
- 출력: Palace가 `postpro/port-S.csv`·`port-V.csv`·`port-I.csv`(+ field) 산출 → 오케스트레이터가 읽어 Z 도출.
- no-ferrite는 upstream material 키(`Permeability`/`Permittivity`/`LossTan`/`Conductivity`)만 사용.
  ferrite 자기손실 config 필드는 GOAL2가 정의 → 그때 orchestrator가 emit(나중).

## 범위 (이번 push)
포함: `inspect_bundle()`(번들 ingest, pydantic, 누락 즉시 fail) ·
`mesh_bundle()`(gmsh tet + physical group 태깅) ·
`solve_bundle()`(no-ferrite 단일주파수 6.78 MHz, Palace wrapper, CUDA+4-core MPI) · 출력 스키마
(`em_result.json`·`network.csv`·`derived.csv`·`port_vi.csv`·`solver_manifest.json`).
제외: ferrite(복소 μ, GOAL2 후) · sweep/SRF/C · loss/field · Mode 2/3 추론.

## 입력 번들 계약 (`<bundle_dir>`, 5파일 전부 — 우회 없음)
- `ssw_scene.step` · `ssw_step_ledger.json`(`bodies[]`,`*_body_names`,`units`) ·
  `ssw_aedt_port_ledger.json`(`port_edges[]` role tx/rx + `edge_vertices_xyz` 쌍 + `copper_body_name`) ·
  `coil_making_token.toml` · `<design_id>.toml`(frequency 6.78 MHz, material, ferrite flag) ·
  + `solver/data/materials.toml`(물성 SSOT).

## Hard Rules (위반 시 즉시 실패 — degrade 금지)
- **CUDA mandatory.** Palace 엔진은 CUDA-only. 오케스트레이터가 invoke 전 GPU 게이트(`nvidia-smi`)를 통과하지 못하면 즉시 exception. **CPU 폴백 없음.**
- **아키텍처 경계.** 오케스트레이터는 Python(도커 밖). 도커 안에 Python 넣지 않음. C++ 드라이버 부활 금지.
- **No pfsolver CLI.** 사용자/peetsfea-facing 진입점은 Python API뿐이다. CLI wrapper/entrypoint/console script를 만들지 않는다.
- **Full-wave only.** Palace `Driven`. MQS/electrostatic/Q3D 도피 금지.
- **Fail-fast.** 키 누락·port 쌍 불일치·material 미정의·units≠mm·port count≠(tx1+rx1) → 즉시 raise. silent fallback 금지.
- **Mock/stub 금지.** `network.csv`·`port_vi.csv`를 가짜로 생성하면 미완. **Palace 실제 실행** port-S/V/I 후처리만 인정.
- **no-ferrite 경계.** ferrite enabled 번들에서 lossless ferrite로 조용히 대체 = 실패. ferrite enabled면 fail-fast 또는 명시적 no-ferrite fixture(ferrite 논모델/제외)만.
- **부호 계약.** Z12/Z21은 HFSS port current 방향 기준 고정. Z는 Palace `port-S.csv`에서 S→Z로 산출하고, `port-V.csv`의 `V_inc`+total V로 재구성한 S가 `port-S.csv`와 일치해야 한다. raw `port-I.csv`는 audit 산출물로 보존한다.
- **재현성.** `solver_manifest.json`: Palace commit, pfsolver commit, palace run command, mesh hash, config hash, GPU name/VRAM, MPI ranks, HYPRE pool, design_id/provenance, wall time, 수렴 정보.

## 교차검증 의존성 — HFSS no-ferrite 기준값 (GOAL2)
pfsolver no-ferrite와 맞댈 정답이 없다(현재 HFSS는 ferrite-enabled). HFSS no-ferrite 1회 실행과 교차검증 §3.2 채움은 GOAL2가 담당한다.
- 입력 `src/peetsfea/data/0.3.x_fixed.toml`(design_id `0_3_7_p6561d2a5c7808f6e`) · TX MULL ferrite를 **non-model**
  (`hfss.modeler.set_object_model_state(<ferrite>, False)`, ssw_ports.py) · 동일 `Setup1 @ 6.78MHz` solve ·
  기존 출력변수(`Ltx/Lrx/M/k/Q/Z`) 추출 · `peetsfea-main/.venv` pyaedt, warm ansysedt attach.
- 증거: report CSV + 로그 + ferrite non-model 확인 + §3.2 채움(ferrite 대비 L↓·k↓ sanity).
- 나중에 Palace field output에서 E/H 또는 B-field plot 이미지를 생성해
  `docs/solver-vs-hfss-crossvalidation-plan.html`에 실제 이미지로 첨부한다(테이블 숫자만 남기지 않음).

## 완료 증거 패키지 (리뷰 시 제출)
Palace wrapper + Python API 호출 코드/로그 · `inspect_bundle(...).to_json()` 출력 · negative pytest 로그(파일 누락·port 불일치·GPU 없음 raise) ·
gmsh mesh/group summary · Palace **config 검증(validate-config/schema/dry-run)** 통과 로그 ·
Palace 실행 command + stdout/stderr · `port-S/V/I.csv`·`network.csv`·`solver_manifest.json` 경로 ·
`solver/pfsolver` pytest(unit/integration) + **pyright strict** 통과.

## 현재 증거 (2026-06-19)
- `solver/pfsolver` 독립 서브모듈: Python API만 제공, console script 없음.
- `../../.venv/bin/pyright` → 0 errors, `../../.venv/bin/python -m pytest -q` → 11 passed.
- stock `palace:0.16.1` 로컬 이미지 build 완료(`localhost/palace:0.16.1`, image `8df41bb914ac`, source `d2b68b6` stock packaging baseline) 및 `~/.local/bin/palace --help/--version` wrapper 동작 확인.
- `run/ssw_0_3_0_fixed` inspect: body 11 / copper 2 / fr4 4 / ferrite 1 / non_model 4.
- `run/pfsolver_no_ferrite_bundle` inspect: copper 2 / fr4 4 / ferrite 0 / non_model 4, ferrite_enabled=false.
- `run/pfsolver_no_ferrite_mesh/mesh.msh` · `mesh_tags.json` · `palace_config.json` 생성, body tags 10 / port tags 2 / absorbing boundary 999.
- Palace JSON schema 검증 및 `~/.local/bin/palace -dry-run palace_config.json` 통과.
- `pfsolver.solve_bundle(..., mpi_ranks=1)` 진단 solve 완료: `run/pfsolver_no_ferrite_solve_rank1/network.csv` · `derived.csv` · `port_vi.csv` · `solver_manifest.json`; manifest `pfsolver_commit=8111dd2177eaade60262ada970d3e65e7b681d1f`, wall time 26.0 s, Palace stdout에 `GMRES solver converged in 3 iterations` 2회 기록.
- `pfsolver.solve_bundle(..., mpi_ranks=2)` MPI 진단 solve 완료: `run/pfsolver_no_ferrite_solve_rank2/*`; manifest wall time 28.5 s, Palace peak memory total 1.8 GiB, HYPRE pool override가 rank별 적용됨.
- `pfsolver.solve_bundle(..., mpi_ranks=4)` 기본 acceptance solve 완료: `run/pfsolver_no_ferrite_solve_rank4/network.csv` · `derived.csv` · `port_vi.csv` · `solver_manifest.json`; manifest `pfsolver_commit=a5cb138cf50473f905c24552e444a903fa0121bc`, wall time 27.2 s, Palace stdout에 `Running with 4 MPI processes` 및 `GMRES solver converged in 3 iterations` 2회 기록.
- phase0 HYPRE OOM 경로 통과: 4-rank stderr에 HYPRE pool override 4회 적용(`device=86654976`, `unified=86654976`, `pinned=16777216`), Palace peak memory total 3.1 GiB.
- HFSS no-ferrite 기준선 완료: `run/hfss_no_ferrite_fixed_full/Results1_Pass.csv` · `Results2_Last.csv` · `Results3_Freq.csv`; ferrite body 0, non_model 4, `Setup1 @ 6.78MHz`, 11 pass, sweep 0.1–100 MHz 81pt, solve 592.7 s. 기준값: Ltx 5.6732 µH, Lrx 5.0391 µH, M 0.1523 µH, k 0.02849, R1 0.2798 Ω, R2 0.2151 Ω.
- HFSS numeric cross-validation은 FAIL: rank4 pfsolver 값은 Ltx 1.05e-9 µH, Lrx 5.17e-10 µH, M 6.07e-16 µH, R1 0.000421 Ω, R2 0.000424 Ω로 HFSS 대비 약 100% 낮다. API/solver orchestration acceptance는 닫혔지만, HFSS 동등 수치 재현은 Palace conductor boundary + air-domain/absorbing-boundary 모델링 보정 후 별도 진행한다.

## Acceptance
Phase A — `inspect`
- [x] `pfsolver.inspect_bundle(Path("run/ssw_0_3_0_fixed"))` → body 11 / copper 2 / fr4 4 / ferrite 1 / non_model 4, port tx 1·rx 1.
- [x] 번들 파일 1개 지우면 pydantic/contract exception으로 즉시 실패(unit test).
- [x] `Scene.to_json()`이 body·port 좌표·freq·material·ferrite flag를 빠짐없이 직렬화.
- [x] 파서 pytest + pyright strict 통과.

Phase B — `mesh` + config 검증
- [x] gmsh 무에러 `mesh.msh` + group↔role 태그, group이 inspect 모델과 1:1.
- [x] emit한 Palace config가 JSON schema 검증 통과.
- [x] `~/.local/bin/palace -dry-run palace_config.json` 실행 통과(`palace:0.16.1`).
- [x] minimal two-port에서 S/Z 2×2·단위·상반성(Z=Zᵀ); `port-S.csv`와 `V_inc`+total V 재구성 S 일치(부호 포함).
  - 증거: `solver/pfsolver/tests/test_post.py`가 `network.csv` 2×2 `s*`/`z*_ohm` 컬럼, S→Z 값, `port-S.csv`↔`port-V.csv` 불일치 raise, non-reciprocal Z raise를 검증.

Phase C — `solve`(no-ferrite, 단일주파수)
- [x] `pfsolver.solve_bundle(bundle_dir=..., mpi_ranks=1)`가 Palace wrapper를 GPU로 완주 → network/derived/port_vi/manifest 생성(진단 실제 실행).
- [x] `pfsolver.solve_bundle(bundle_dir=..., mpi_ranks=2)`가 Palace wrapper MPI 경로로 완주(진단 실제 실행).
- [x] 기본 `mpi_ranks=4` acceptance solve가 RTX 3070에서 완주.
- [x] GPU 미부착 시 즉시 exception(폴백 없음, unit test).
- [x] phase0 HYPRE OOM이 VRAM/MPI-rank 적응 pool로 통과(8 GB RTX 3070, 4-rank).
- [x] rank1 manifest 재현 필드 전부.

## Definition of Done
`inspect_bundle`·`mesh_bundle`·`solve_bundle`가 no-ferrite 단일주파수에서 Palace 실제 실행으로 `network.csv`를 만들고,
manifest/port audit 산출물을 남긴다. HFSS no-ferrite와의 **부호/shape/단위 일치** 및 numeric tolerance는 GOAL2의 §3.2 기준값이 채워진 뒤에 판정한다.
