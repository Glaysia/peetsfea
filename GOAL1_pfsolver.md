# GOAL 1 — `pfsolver` Python 오케스트레이터 (스트림 A)

병렬 작업 둘 중 **A**. 짝: [GOAL2_forked_palace.md](GOAL2_forked_palace.md)(Palace 포크/μ 패치).
이 스트림은 **Python 오케스트레이터**를 만든다. **no-ferrite는 GOAL2의 μ 패치 없이 진행 가능**하다(아래 병렬성 참고).

## 목표
`pfsolver inspect|mesh|solve`가 동작하고, **no-ferrite 단일주파수(6.78 MHz)** 에서 도커 안 Palace를
호출해 2-포트 terminal Z를 산출, HFSS no-ferrite와 부호/shape/단위가 일치하는 상태까지.

## 아키텍처 (pyaedt → ansysedt 구도)
- `pfsolver` = **Python 오케스트레이터** (pyright strict + pydantic), **도커 밖**, peetsfea 생태계 안.
- 역할: 번들 ingest → **gmsh(Python API)** 메시 → Palace `Driven` config(JSON) emit →
  **도커 Palace를 CLI 호출**(JSON in / CSV out) → CSV→Z 후처리 → manifest.
- 도커 안엔 **forked Palace 엔진만**(GOAL2 산출 `peetsfea-palace:dev`). 오케스트레이터엔 C++ 없음.

## 병렬성 (GOAL2와의 경계)
- **Phase A(inspect)·B(mesh·config·dry-run)** 는 Palace solve가 필요 없다 → **GOAL2와 완전 병렬, 의존 0.**
- **Phase C(solve)** 만 도커 Palace 이미지가 필요 → **GOAL2의 M1(upstream-동등 빌드)** 이면 충분(μ 패치 불필요).
  no-ferrite는 upstream Palace 기능만 쓴다.
- **ferrite(복소 μ)** 만 GOAL2의 M-fork에 의존 → 이번 push 범위 밖(나중).
- 임시 unblock: GOAL2 이미지 전이라도 Phase C는 stock upstream `palace` 이미지로 개발/테스트 가능(no-ferrite라 동등).

## Palace 인터페이스 계약 (GOAL2와 합의된 경계 — 깨지면 안 됨)
- 입력: 오케스트레이터가 **Palace `Driven` config(JSON)** + **mesh(.msh)** 를 emit.
- 호출: `palace <config.json>` (도커 안), MPI 4 rank, `Solver.Device=GPU`.
- 출력: Palace가 `postpro/port-S.csv`·`port-V.csv`·`port-I.csv`(+ field) 산출 → 오케스트레이터가 읽어 Z 도출.
- no-ferrite는 upstream material 키(`Permeability`/`Permittivity`/`LossTan`/`Conductivity`)만 사용.
  ferrite 자기손실 config 필드는 GOAL2가 정의 → 그때 orchestrator가 emit(나중).

## 범위 (이번 push)
포함: `inspect`(번들 ingest, pydantic, 누락 즉시 fail) · `mesh`(gmsh tet + physical group 태깅) ·
`solve`(no-ferrite 단일주파수 6.78 MHz, 도커 Palace, CUDA+4-core MPI) · 출력 스키마
(`em_result.json`·`network.csv`·`derived.csv`·`port_vi.csv`·`solver_manifest.json`).
제외: ferrite(복소 μ, GOAL2 후) · sweep/SRF/C · loss/field · Mode 2/3 추론.

## 입력 번들 계약 (`<bundle_dir>`, 5파일 전부 — 우회 없음)
- `ssw_scene.step` · `ssw_step_ledger.json`(`bodies[]`,`*_body_names`,`units`) ·
  `ssw_aedt_port_ledger.json`(`port_edges[]` role tx/rx + `edge_vertices_xyz` 쌍 + `copper_body_name`) ·
  `coil_making_token.toml` · `<design_id>.toml`(frequency 6.78 MHz, material, ferrite flag) ·
  + `solver/data/materials.toml`(물성 SSOT).

## Hard Rules (위반 시 즉시 실패 — degrade 금지)
- **CUDA mandatory.** 도커 Palace는 CUDA-only. 오케스트레이터가 invoke 전 GPU 게이트(`nvidia-smi`), 없으면 exit≠0. **CPU 폴백 없음.**
- **아키텍처 경계.** 오케스트레이터는 Python(도커 밖). 도커 안에 Python 넣지 않음. C++ 드라이버 부활 금지.
- **Full-wave only.** Palace `Driven`. MQS/electrostatic/Q3D 도피 금지.
- **Fail-fast.** 키 누락·port 쌍 불일치·material 미정의·units≠mm·port count≠(tx1+rx1) → 즉시 raise. silent fallback 금지.
- **Mock/stub 금지.** `network.csv`·`port_vi.csv`를 가짜로 생성하면 미완. **Palace 실제 실행** port-S/V/I 후처리만 인정.
- **no-ferrite 경계.** ferrite enabled 번들에서 lossless ferrite로 조용히 대체 = 실패. ferrite enabled면 fail-fast 또는 명시적 no-ferrite fixture(ferrite 논모델/제외)만.
- **부호 계약.** Z12/Z21은 HFSS port current 방향 기준 고정. S→Z와 V/I→Z 두 경로 일치.
- **재현성.** `solver_manifest.json`: Palace commit, pfsolver commit, palace run command, mesh hash, config hash, GPU name/VRAM, MPI ranks, HYPRE pool, design_id/provenance, wall time, 수렴 정보.

## 선행 task — HFSS no-ferrite 기준값 (이 스트림에 포함)
pfsolver no-ferrite와 맞댈 정답이 없다(현재 HFSS는 ferrite-enabled). HFSS no-ferrite 1회 실행해 교차검증 §3.2 채움.
- 입력 `src/peetsfea/data/0.3.x_fixed.toml`(design_id `0_3_7_p6561d2a5c7808f6e`) · TX MULL ferrite를 **non-model**
  (`hfss.modeler.set_object_model_state(<ferrite>, False)`, ssw_ports.py) · 동일 `Setup1 @ 6.78MHz` solve ·
  기존 출력변수(`Ltx/Lrx/M/k/Q/Z`) 추출 · `peetsfea-main/.venv` pyaedt, warm ansysedt attach.
- 증거: report CSV + 로그 + ferrite non-model 확인 + §3.2 채움(ferrite 대비 L↓·k↓ sanity).

## 완료 증거 패키지 (리뷰 시 제출)
docker run + pfsolver command · `inspect --json` 출력 · negative test 로그(파일 누락·port 불일치·GPU 없음 exit≠0) ·
gmsh mesh/group summary · Palace **config 검증(validate-config/schema/dry-run)** 통과 로그 ·
Palace 실행 command + stdout/stderr · `port-S/V/I.csv`·`network.csv`·`solver_manifest.json` 경로 ·
pytest(unit/integration) + **pyright strict** 통과.

## Acceptance
Phase A — `inspect`
- [ ] `pfsolver inspect run/ssw_0_3_0_fixed` → exit 0, body 11 / copper 2 / fr4 4 / ferrite 1 / non_model 4, port tx 1·rx 1.
- [ ] 번들 파일 1개 지우면 exit≠0(pydantic).
- [ ] `--json`이 Scene(body·port 좌표·freq·material·ferrite flag) 빠짐없이 직렬화.
- [ ] 파서 pytest + pyright strict 통과.

Phase B — `mesh` + config 검증
- [ ] gmsh 무에러 `mesh.msh` + group↔role 태그, group이 inspect 모델과 1:1.
- [ ] emit한 Palace config가 validate-config/dry-run 통과.
- [ ] minimal two-port에서 S/Z 2×2·단위·상반성(Z=Zᵀ); S→Z와 V/I→Z 두 경로 일치(부호 포함).

Phase C — `solve`(no-ferrite, 단일주파수)
- [ ] `pfsolver solve <bundle>`가 도커 Palace를 GPU로 완주 → network/derived/port_vi/manifest 생성(실제 실행).
- [ ] GPU 미부착 시 즉시 실패(폴백 없음).
- [ ] phase0 HYPRE OOM이 VRAM 적응 pool로 통과(8 GB RTX 3070).
- [ ] manifest 재현 필드 전부.

## Definition of Done
`inspect|mesh|solve`가 no-ferrite 단일주파수에서 Palace 실제 실행으로 `network.csv`를 만들고, Z가 HFSS
no-ferrite와 **부호/shape/단위 일치**. numeric tolerance는 §3.2 기준값 채워진 뒤에만 요구.
