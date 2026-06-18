# GOAL: `pfsolver`로 Phase A–C를 한 번에 — HFSS 없이 no-ferrite 단일주파수 Z(f) 재현

이 브랜치(dev/3)의 목표는 Ansys HFSS를 대체하는 오픈소스 full-wave 솔버 `pfsolver`다.
이번 push의 목표는 **Phase A→B→C를 단번에 밀어** `pfsolver inspect|mesh|solve`가 동작하고,
**no-ferrite 단일주파수(6.78 MHz)** 에서 forked Palace `Driven`(full-wave)가 2-포트 terminal Z를
산출해 HFSS와 부호/shape/단위가 일치하는 상태까지 가는 것이다.

- 상세 계획: [solver/docs/implementation-plan-phase-A-C.md](solver/docs/implementation-plan-phase-A-C.md)
- 큰 그림: [cpp-cuda-fem-solver-longterm-plan.html](cpp-cuda-fem-solver-longterm-plan.html)
- 교차검증 기준값(HFSS): [docs/solver-vs-hfss-crossvalidation-plan.html](docs/solver-vs-hfss-crossvalidation-plan.html)

## 아키텍처 (확정)
**pyaedt → ansysedt 구도와 동일.** Python이 오케스트레이션, C++ 엔진은 도커 안.
- **pfsolver = Python 오케스트레이터** (정적 타입: pyright strict + pydantic). peetsfea 생태계 안에서
  하던대로 동작한다. 역할: 번들 ingest → gmsh(Python API) 메시 → Palace config(JSON) emit →
  **도커 안 forked Palace를 CLI 호출**(JSON in / CSV out) → CSV→Z 후처리 → manifest.
- **Docker = forked Palace 엔진만** (`peetsfea-palace:dev`). CUDA C++ FEM 코어 + 추후 복소 μ 패치.
  유일하게 컨테이너화되는 것. pfsolver는 도커 밖 Python.
- **C++은 forked Palace 안에만.** 오케스트레이터엔 C++ 없음(CLI-only면 C++일 이유가 없으므로).
- **Palace 계약 = CLI(JSON config / CSV).** Palace엔 stable 공개 libpalace가 없으므로 안정 인터페이스는 CLI뿐.

## 모드 로드맵 (이 push = Mode 1)
- **Mode 1 = FEM** (지금 만드는 것). forked Palace로 정밀 Z(f) 산출.
- Mode 1 완성 후 **데이터셋을 대량 축적** → transformer 모델은 **다른 프로젝트에서 학습/배포**.
- **Mode 2/3 = pfsolver에서 추론만.** 배포된 모델을 호출(warm-start FEM / surrogate-only). 학습은 안 함.

## 작업 방식 (중요)
- **구현은 Codex가 한다.** 한 번에 Phase A–C를 진행한다.
- **Claude(나)는 1시간마다 호출되어 평가/피드백만 한다.** 코드를 다시 짜지 않고, 이 GOAL.md의
  Acceptance와 Hard Rules 기준으로 진행 상태를 검수한다.
- Acceptance는 **객관적으로 체크 가능**해야 하며, Codex는 각 항목을 실제 명령 출력/테스트로 증명한다(주장만으로 "완료" 금지).

## 범위 (이번 push)
포함:
- `pfsolver inspect <bundle>` — 번들 5종을 pydantic으로 파싱 → Scene 모델 복원, 누락 즉시 fail.
- `pfsolver mesh <bundle>` — gmsh(Python)로 STEP→tet, physical group으로 copper/FR4/(ferrite)/port/boundary 태깅.
- `pfsolver solve <bundle>` — 도커 forked Palace `Driven`, lumped terminal 2포트, **no-ferrite 단일주파수 6.78 MHz**, CUDA + 4-core MPI → `network.csv` 등.
- 출력 스키마: `em_result.json`, `network.csv`, `derived.csv`, `port_vi.csv`, `solver_manifest.json`.

제외(이번 push 아님):
- ferrite(복소 μ) — Palace fork 패치(M-fork)가 선행. 이번엔 no-ferrite만.
- frequency sweep / SRF / C 추출, loss.csv / field_index.json(field 산출).
  - (참고) sweep이 들어올 땐 **HFSS terminal 방식 = 단일 주파수에서 확정한 메시를 다주파수에 재사용**(주파수마다 재적응 안 함; Palace Driven native). 이번 push는 단일 주파수만.
- Mode 2/3(추론) — 모델이 아직 없음(다른 프로젝트).

## 입력 번들 계약
`<bundle_dir>` 안의 5파일을 모두 읽는다(우회 없음). STEP 단독은 material/port/boundary가 없다.
- `ssw_scene.step` — geometry
- `ssw_step_ledger.json` — `bodies[]`(role·material·center·size), `*_body_names`, `units`
- `ssw_aedt_port_ledger.json` — `port_edges[]`(role tx/rx, `edge_vertices_xyz` 쌍, `copper_body_name`)
- `coil_making_token.toml` — metadata(seed·schema·spec), actions
- `<design_id>.toml` — frequency 6.78 MHz, material 참조, ferrite enable flag
- + `solver/data/materials.toml`(물성 SSOT: copper σ=5.8e7, FR4 εr 4.4/tanδ 0.02, air/vacuum, ferrite 복소 μ)

## Hard Rules (위반 시 즉시 실패 — degrade 금지)
- **CUDA mandatory.** Palace 도커 이미지는 CUDA-only 빌드. pfsolver는 invoke 전 GPU 게이트(`nvidia-smi`/cudaMemGetInfo), 없으면 exit≠0. **CPU 폴백 절대 없음.**
- **Docker 안 = forked Palace만.** 오케스트레이터(Python)는 도커 밖. 도커 안에 Python 오케스트레이터를 넣지 않는다.
- **Full-wave only.** forked Palace `Driven`(변위전류 포함). MQS/electrostatic/Q3D로의 도피 금지.
- **Fail-fast.** 번들 키 누락·port 쌍 불일치·material 미정의·units≠mm·port count≠(tx1+rx1)이면 즉시 raise. silent fallback/log-and-continue/degraded geometry 금지.
- **Mock/stub 금지.** `network.csv`·`port_vi.csv`를 가짜 값으로 생성하면 **완료 아님**. 반드시 forked Palace **실제 실행**으로 `port-S/V/I.csv`가 나온 뒤 후처리한 값만 인정.
- **no-ferrite 경계.** 이번 solve는 no-ferrite만. ferrite enabled 번들에서 upstream Palace 한계 때문에 **lossless ferrite로 조용히 대체하면 실패**. ferrite enabled인데 M-fork 전 solve = fail-fast, 또는 명시적 no-ferrite fixture(ferrite 논모델/제외)로만 진행.
- **부호 계약.** Z12/Z21은 HFSS port current 방향 기준 고정. S→Z와 V/I→Z 두 경로가 일치.
- **재현성.** solve는 `solver_manifest.json`에 다음을 모두 남긴다: forked Palace commit, pfsolver commit, palace run command, mesh hash, config hash, GPU name/VRAM, MPI ranks, HYPRE pool 설정, bundle design_id/provenance, wall time, 수렴 정보.

## 선행 task — HFSS no-ferrite 기준값 생성 (Codex, 이 push에 포함)
pfsolver no-ferrite와 맞댈 정답 기준선이 아직 없다(현재 HFSS 값은 ferrite-enabled). Codex가 이 push에서
HFSS no-ferrite를 1회 돌려 교차검증 문서 §3.2를 채운다.
- 입력: `src/peetsfea/data/0.3.x_fixed.toml`(design_id `0_3_7_p6561d2a5c7808f6e`, 동일 형상).
- 방법: TX MULL ferrite body를 **non-model**로 — `hfss.modeler.set_object_model_state(<ferrite_name>, False)`(ssw_ports.py에 존재). 형상 유지, EM solve에서만 제외.
- solve: 동일 `Setup1 @ 6.78MHz`, 4 cores, GPU. 추출은 기존 출력변수(`Ltx_uH/Lrx_uH/M_uH/k_ratio/Qtx/Qrx/re|im Z11/Z12/Z22`).
- 환경: `peetsfea-main/.venv`(pyaedt), warm ansysedt attach.
- 산출/증거: report CSV 경로 + solve 로그 + ferrite non-model 확인 + **§3.2 표 채움**, ferrite 대비 L↓·k↓ sanity.

## 완료 증거 패키지 (각 리뷰 시 Codex가 제출)
"완료"는 주장이 아니라 아래 산출물로 증명한다. 없으면 미완.
- 실행한 docker build/run + pfsolver **command** 원문.
- `pfsolver inspect --json` 산출물.
- **negative test 로그**(파일 누락·port 불일치·GPU 없음 → exit≠0).
- gmsh **mesh/group summary** + Palace **config 검증**(`palace`의 schema/validate-config 또는 dry-run) 통과 로그.
- forked Palace **실행 command + stdout/stderr**.
- 실제 파일 경로: `port-S.csv`·`port-V.csv`·`port-I.csv`·`network.csv`·`solver_manifest.json`.
- 관련 **pytest(unit/integration) 결과** + **pyright strict** 통과.

## Acceptance Criteria (Claude 검수 체크리스트)
Phase A — `inspect`
- [ ] `pfsolver inspect run/ssw_0_3_0_fixed` → exit 0. body 11 / copper 2 / fr4 4 / ferrite 1 / non_model 4, port tx 1·rx 1 정확 보고.
- [ ] 번들 파일 1개 지우면 명확한 메시지로 exit≠0 (pydantic 검증).
- [ ] `--json` 출력이 Scene 모델(body·port 좌표·freq·material·ferrite flag)을 빠짐없이 직렬화.
- [ ] 파서 pytest(fixed 번들 fixture 골든값) 통과 + pyright strict 통과.

Phase B — `mesh` + config 검증 + V0 two-port
- [ ] `pfsolver mesh`가 gmsh 무에러로 `mesh.msh` + group↔role 태그 산출, group이 inspect 모델과 1:1.
- [ ] emit한 Palace config가 **config 검증(validate-config/schema/dry-run)** 통과 — 잘못된 JSON/attribute mapping은 solve 전에 잡는다.
- [ ] minimal two-port에서 S/Z가 2×2·올바른 단위·상반성(Z=Zᵀ) 만족.
- [ ] S→Z와 V/I→Z 두 경로가 tight 일치(부호 포함).

Phase C — `solve`(no-ferrite, 단일주파수)
- [ ] `pfsolver solve <bundle>`가 도커 Palace를 GPU로 완주 → `network.csv`/`derived.csv`/`port_vi.csv`/`solver_manifest.json` 생성(forked Palace 실제 실행).
- [ ] GPU 미부착 시 즉시 실패(폴백 없음) 재확인.
- [ ] phase0 HYPRE OOM 케이스가 VRAM 적응 pool로 통과(8 GB RTX 3070).
- [ ] manifest에 재현 필드 전부 존재.

## Definition of Done (이번 push)
`pfsolver inspect|mesh|solve`가 fixed 번들의 **no-ferrite 단일주파수**에서 끝까지 돌아 (forked Palace
실제 실행으로) `network.csv`를 만들고, 그 Z가 HFSS no-ferrite terminal Z와 **부호·shape·단위가 일치**하며,
위 Acceptance 전 항목이 실제 출력으로 증명된다.
- 1차 DoD = **부호/shape/단위 일치**.
- **numeric tolerance**(L/M/R 수치 오차)는 **§3.2 no-ferrite HFSS 기준값이 채워진 뒤에만** 요구. 그 전엔 "준비/기록".

## Claude 시간별 리뷰가 볼 것 (특히 강하게)
1. **실제 Palace run 증거** — mock/stub로 채운 CSV는 미완.
2. **아키텍처 경계** — 오케스트레이터는 Python(도커 밖), 도커 안은 forked Palace만. C++ 드라이버 부활 금지.
3. **no-ferrite/ferrite 경계** — lossless ferrite 조용한 대체 금지.
4. **manifest 재현성** — 위 필드 전부.
5. Hard Rules 위반(CPU 폴백·silent degrade·full-wave 이탈).
6. Acceptance 항목별 **증거** 유무 — 주장만이면 미완. pyright strict + pytest 통과.
7. 다음 1시간 우선순위 제안(막힌 지점 unblock 위주).
