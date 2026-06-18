# GOAL: `pfsolver`로 Phase A–C를 한 번에 — HFSS 없이 no-ferrite 단일주파수 Z(f) 재현

이 브랜치(dev/3)의 목표는 Ansys HFSS를 대체하는 오픈소스 CUDA full-wave 솔버
`pfsolver`다. 이번 push의 목표는 **Phase A→B→C를 단번에 밀어** `pfsolver
inspect|mesh|solve`가 동작하고, **no-ferrite 단일주파수(6.78 MHz)** 에서 forked
Palace `Driven`(full-wave)가 2-포트 terminal Z를 산출해 HFSS와 부호/shape/단위가
일치하는 상태까지 가는 것이다.

- 상세 계획(task/struct/acceptance): [solver/docs/implementation-plan-phase-A-C.md](solver/docs/implementation-plan-phase-A-C.md)
- 큰 그림: [cpp-cuda-fem-solver-longterm-plan.html](cpp-cuda-fem-solver-longterm-plan.html)
- 교차검증 기준값(HFSS): [docs/solver-vs-hfss-crossvalidation-plan.html](docs/solver-vs-hfss-crossvalidation-plan.html)
- 이미 완료: M0 — Docker 전용 빌드 + `pfsolver doctor`(CUDA 게이트).

## 작업 방식 (중요)
- **구현은 Codex가 한다.** 한 번에 Phase A–C를 진행한다.
- **Claude(나)는 1시간마다 호출되어 평가/피드백만 한다.** 코드를 다시 짜지 않고,
  이 GOAL.md의 Acceptance와 Hard Rules 기준으로 진행 상태를 검수한다.
- 따라서 아래 Acceptance는 **객관적으로 체크 가능**해야 하며, Codex는 각 항목을
  실제 명령 출력/테스트로 증명한다(주장만으로 "완료" 금지).

## 범위 (이번 push)
포함:
- `pfsolver inspect <bundle>` — 번들 5종 파싱 → 내부 Scene 모델 복원, 누락 즉시 fail.
- `pfsolver mesh <bundle>` — STEP→tet, physical group으로 copper/FR4/(ferrite)/port/boundary 태깅.
- `pfsolver solve <bundle>` — forked Palace `Driven`, lumped terminal 2포트, **no-ferrite 단일주파수 6.78 MHz**, CUDA + 4-core MPI → `network.csv` 등.
- 출력 스키마: `em_result.json`, `network.csv`, `derived.csv`, `port_vi.csv`, `solver_manifest.json`.

제외(이번 push 아님):
- ferrite(복소 μ) — Palace fork 패치(M-fork)가 선행. 이번엔 no-ferrite만.
- frequency sweep / SRF / C 추출.
- loss.csv / field_index.json(field 산출), Mode 2 warm-start, Mode 3 label.

## 입력 번들 계약
`<bundle_dir>` 안의 5파일을 모두 읽는다(우회 없음). STEP 단독은 material/port/boundary가 없다.
- `ssw_scene.step` — geometry
- `ssw_step_ledger.json` — `bodies[]`(role·material·center·size), `*_body_names`, `units`
- `ssw_aedt_port_ledger.json` — `port_edges[]`(role tx/rx, `edge_vertices_xyz` 쌍, `copper_body_name`)
- `coil_making_token.toml` — metadata(seed·schema·spec), actions
- `<design_id>.toml` — frequency 6.78 MHz, material 참조, ferrite enable flag
- + `solver/data/materials.toml`(물성 SSOT: copper σ=5.8e7, FR4 εr 4.4/tanδ 0.02, air/vacuum)

## Hard Rules (위반 시 즉시 실패 — degrade 금지)
- **CUDA mandatory.** GPU 없으면 build 실패(`CUDAToolkit REQUIRED`) 또는 run 실패(exit≠0). **CPU 폴백 절대 없음.**
- **Docker 전용.** 호스트 빌드 미지원. 모든 빌드/실행은 `solver/docker/`.
- **Full-wave only.** forked Palace `Driven`(변위전류 포함). MQS/electrostatic/Q3D로의 도피 금지.
- **Fail-fast.** 번들 키 누락·port 쌍 불일치·material 미정의·units≠mm·port count≠(tx1+rx1)이면 즉시 raise. silent fallback/log-and-continue/degraded geometry 금지.
- **부호 계약.** Z12/Z21은 HFSS port current 방향 기준으로 고정. S→Z와 V/I→Z 두 경로가 일치해야 한다.
- **Mock/stub 금지.** `network.csv`·`port_vi.csv`를 테스트용 가짜 값으로 생성하면 **완료 아님**. 반드시 forked Palace `Driven` **실제 실행**으로 `port-S/V/I.csv`가 나온 뒤 후처리한 값만 인정.
- **no-ferrite 경계.** 이번 solve는 no-ferrite만이다. ferrite enabled 번들에서 upstream Palace 한계 때문에 **lossless ferrite로 조용히 대체하면 실패**로 본다. ferrite enabled인데 M-fork 전 solve 시도 = fail-fast, 또는 명시적 no-ferrite fixture(ferrite 논모델/제외)로만 진행.
- **재현성.** solve는 `solver_manifest.json`에 다음을 모두 남긴다: forked Palace commit, pfsolver commit, run command, mesh hash, config hash, GPU name/VRAM, MPI ranks, HYPRE pool 설정, bundle design_id/provenance, wall time, 수렴 정보.

## Acceptance Criteria (Claude 검수 체크리스트)
Phase A — `inspect`
- [ ] `pfsolver inspect run/ssw_0_3_0_fixed` → exit 0. body 11 / copper 2 / fr4 4 / ferrite 1 / non_model 4, port tx 1·rx 1을 정확히 보고.
- [ ] 번들 파일 1개를 지우면 명확한 메시지로 exit≠0.
- [ ] `--json` 출력이 Scene 모델(body·port 좌표·freq·material·ferrite flag)을 빠짐없이 직렬화.
- [ ] 파서별 단위테스트(fixed 번들 fixture 골든값) 통과.

Phase B — `mesh` + config 검증 + V0 two-port
- [ ] `pfsolver mesh`가 gmsh 무에러로 `mesh.msh` + group↔role 태그 산출, group이 inspect 모델과 1:1.
- [ ] emit한 Palace config가 **`palace --dry-run`(또는 동등 config parse 검증)** 통과 — 잘못된 JSON/schema/attribute mapping은 solve 전에 잡는다.
- [ ] minimal two-port에서 S/Z가 2×2·올바른 단위·상반성(Z=Zᵀ) 만족.
- [ ] S→Z와 V/I→Z 두 경로가 tight 일치(부호 포함).
- [ ] (no-ferrite HFSS 기준값이 준비된 경우) 저복잡도 L/R가 mesh refine 후 tolerance 내 수렴.

Phase C — `solve`(no-ferrite, 단일주파수)
- [ ] `pfsolver solve <bundle>`가 GPU에서 완주 → `network.csv`/`derived.csv`/`port_vi.csv`/`solver_manifest.json` 생성.
- [ ] GPU 미부착 시 즉시 실패(폴백 없음) 재확인.
- [ ] phase0의 HYPRE OOM 케이스가 VRAM 적응 pool로 통과(8 GB RTX 3070).
- [ ] manifest에 재현 필드 전부 존재.

## 완료 증거 패키지 (각 리뷰 시 Codex가 제출)
"완료"는 주장이 아니라 아래 산출물로 증명한다. 없으면 미완.
- 실행한 Docker **build/run command** 원문.
- `pfsolver inspect --json` 산출물.
- **negative test 로그**(파일 누락·port 불일치·GPU 없음 → exit≠0).
- gmsh **mesh/group summary** + Palace **config `--dry-run`** 통과 로그.
- forked Palace **실행 command + stdout/stderr**.
- 실제 파일 경로: `port-S.csv`·`port-V.csv`·`port-I.csv`·`network.csv`·`solver_manifest.json`.
- 관련 **unit/integration test 결과**.

## Definition of Done (이번 push)
`pfsolver inspect|mesh|solve`가 fixed 번들의 **no-ferrite 단일주파수**에서 끝까지
돌아 (forked Palace 실제 실행으로) `network.csv`를 만들고, 그 Z가 HFSS terminal Z와
**부호·shape·단위가 일치**하며, 위 Acceptance 전 항목이 실제 출력으로 증명된다.
- 1차 DoD = **부호/shape/단위 일치**.
- **numeric tolerance**(L/M/R 수치 오차)는 **no-ferrite HFSS 기준값이 있을 때만** 요구한다.
  현재 HFSS 기준값은 ferrite-enabled라, no-ferrite 기준은 별도로 다시 뽑는다(→ 진행 중).
  기준값 확보 전에는 numeric parity를 "준비/기록"으로 둔다.
그 시점에 교차검증 문서 §4·§5의 pfsolver 열을 no-ferrite 행부터 채우기 시작한다.

## Claude 시간별 리뷰가 볼 것 (특히 강하게)
1. **실제 Palace run 증거** — mock/stub로 채운 CSV는 미완.
2. **no-ferrite/ferrite 경계** — lossless ferrite 조용한 대체 금지.
3. **manifest 재현성** — 위 필드 전부 존재.
4. Hard Rules 위반(CPU 폴백·silent degrade·full-wave 이탈).
5. Acceptance 항목별 **증거**(명령 출력/테스트 로그) 유무 — 주장만이면 미완.
6. 입력 번들 계약(5파일 전부, fail-fast 실동작), 부호/단위/상반성 물리 계약.
7. 다음 1시간 우선순위 제안(막힌 지점 unblock 위주).
