# pfsolver — Phase A–C 구체 구현 계획

목적: `pfsolver`가 Ansys 없이 0.3.7 STEP 번들을 받아 HFSS terminal-network Z(f)를
재현하는 경로의 **첫 세 단계**를 task/struct/acceptance 수준까지 구체화한다.

- 상위 문서: [`../../cpp-cuda-fem-solver-longterm-plan.html`](../../cpp-cuda-fem-solver-longterm-plan.html)
  (§6 파이프라인·§11 로드맵), 교차검증 [`../../docs/solver-vs-hfss-crossvalidation-plan.html`](../../docs/solver-vs-hfss-crossvalidation-plan.html)
> **아키텍처 (확정, pyaedt→ansysedt 구도):** `pfsolver`는 `solver/pfsolver` 아래의
> **독립 Python API 서브프로젝트**(pyright strict + pydantic)다.
> peetsfea-facing CLI는 만들지 않는다. peetsfea는 나중에 Python API를 import/call한다.
> **도커 안엔 forked Palace 엔진만**(CUDA C++). 오케스트레이터가 도커 palace 엔진을
> **CLI(JSON config / CSV)** 로 호출한다. 이 CLI는 pfsolver 사용자 표면이 아니라 Palace 엔진 경계다.
> (이전 C++ 드라이버 `solver/src/*`는 폐기됨.) gmsh는 **Python API** in-process.

- 코어: **forked Palace** `Driven`(full-wave). CUDA mandatory, 4-core MPI, CPU 폴백 없음.
- **Sweep 모델(중요):** HFSS terminal-network처럼 **단일 주파수(6.78 MHz)에서 메시를 한 번 확정**하고, 그 **같은 메시를 다른 주파수에 재사용**해 sweep한다(주파수마다 re-mesh/재적응하는 "진짜 sweep"은 자원 과다라 안 함). 이는 Palace `Driven`의 native 동작(고정 메시 위 다주파수 해; 필요시 PROM/adaptive fast sweep)과 정확히 일치.

Python API 최종형: `pfsolver.inspect_bundle(bundle_dir)`, `pfsolver.mesh_bundle(bundle_dir, ...)`,
`pfsolver.solve_bundle(bundle_dir, ...)`.
`<bundle_dir>` = 한 seed의 산출 디렉토리(`ssw_scene.step` 등이 들어있는 곳).

---

## 입력 번들 계약 (세 Phase 공통)

| 파일 | 읽는 키 | 복원 대상 |
| --- | --- | --- |
| `ssw_scene.step` | BREP solids | geometry(메시 입력) |
| `ssw_step_ledger.json` | `bodies[]`(object_id·role·material·center_xyz·size_xyz), `copper/ferrite/fr4/non_model_body_names`, `units` | body→domain 분류 |
| `ssw_aedt_port_ledger.json` | `port_edges[]`(role tx/rx, `edge_vertices_xyz` 쌍, `copper_body_name`), `*_body_names` | lumped terminal port edge 쌍 |
| `coil_making_token.toml` | `[metadata]`(seed·schema·spec), `[[actions]]` | semantic 검증·provenance |
| `<design_id>.toml` | `[fixed_dimensions]`, `[ferrite]` enable/ratio, frequency(6.78 MHz), material refs | frequency plan·material 선택·ferrite on/off |
| `solver/data/materials.toml` | copper/air/vacuum/fr4/ferrite 물성(εr·μr·σ·tanδ·복소 μ) | material 상수(SSOT, 이미 확보) |

전역 원칙: **누락·모순이면 즉시 `throw`**(no fallback). 단위는 mm(ledger `units`로 검증).

---

## Phase A — `pfsolver.inspect_bundle` + 출력 스키마

> 목표: "HFSS 없이 setup을 구성할 수 있다"를 증명. 번들을 읽어 solve에 필요한
> 모든 정보를 내부 모델로 복원하고, 누락이면 fail. **출력 스키마는 solve와 함께
> 확정하므로 여기서는 read-side 모델 + `inspect` dump까지.**

### A.1 파서 (`solver/pfsolver/src/pfsolver/ingest.py`)
- `bundle.py` — `<bundle_dir>` 존재/파일 5종 확인, 경로 해석.
- `ledgers.py` — `ssw_step_ledger.json` / `ssw_aedt_port_ledger.json` pydantic 검증.
- `design.py` — `<design_id>.toml` → `FreqPlan` + ferrite enable + material 매핑.
- `materials.py` — `solver/data/materials.toml` → `MaterialDB`.
- JSON: stdlib `json`, TOML: stdlib `tomllib`, 모델: pydantic.

### A.2 내부 모델 (`solver/pfsolver/src/pfsolver/model.py`)
- `Body`: id, role, material, canonical coordinates, model_state.
- `PortEdge`: role(`tx`/`rx`), copper body, `edge_vertices_xyz` 쌍, HFSS current direction metadata.
- `Material`: eps/mu/sigma/loss terms. ferrite complex μ fields are present but solve emission is fail-fast until GOAL2.
- `FreqPlan`: first scope is fixed `6.78e6 Hz`.
- `Scene`: bodies, ports, materials, freq, ferrite flag, provenance.

### A.3 복원 + 검증 규칙 (fail-fast)
- body role과 `*_body_names` 교차검증 → 불일치 fail.
- `port_edges`가 정확히 tx 1 + rx 1, 각 edge가 copper body에 귀속 → 아니면 fail.
- 각 port의 copper_body가 `copper_body_names`에 존재 → 아니면 fail.
- ferrite_enabled=true인데 ferrite body 없음(또는 반대) → fail.
- 모든 material 참조가 `MaterialDB`에 존재 → 아니면 fail.
- units != "mm" → fail.

### A.4 `inspect_bundle` 출력
- Python object `Scene`; `Scene.to_json()`이 body count·roles, port 쌍 좌표,
  freq plan, material 표, ferrite flag를 직렬화한다. 이게 Phase B의 fixture 입력.

### A.5 acceptance
- [ ] `pfsolver.inspect_bundle(Path("run/ssw_0_3_0_fixed"))` → body 11/copper 2/fr4 4/ferrite 1, port tx·rx 각 1.
- [ ] 일부러 파일 1개 지우면 → 명확한 exception.
- [ ] `Scene.to_json()` 출력이 §A.2 모델을 빠짐없이 직렬화.
- [ ] 단위테스트: fixed 번들 fixture로 파서별 골든값 비교.

---

## Phase B — minimal two-port cross-solver check (V0)

> 목표: 가장 단순한 2-포트(코일 아님, copper pad/loop)로 ingest→mesh→solve→Z
> 전 경로를 처음 관통시키고 HFSS와 **부호·shape·단위**를 맞춘다. SSW 코일·ferrite는 아직.

### B.1 메시 (`pfsolver.mesh_bundle`, `solver/pfsolver/src/pfsolver/mesh.py`)
- gmsh Python API로 `ssw_scene.step`(또는 minimal STEP) import(OCCT).
- physical group 부여: 각 Body→domain group, port edge→port group, 외곽 vacuum→boundary.
- copper edge·port gap refine, 출력 `mesh.msh`(Palace 호환 포맷) + `mesh_tags.json`(group↔role).
- acceptance: group 수·태깅이 `inspect` 모델과 1:1, gmsh 무에러.

### B.2 config emit (`solver/pfsolver/src/pfsolver/palace_config.py`)
- `Scene` + mesh tags → forked Palace `Driven` config(JSON):
  `Problem.Type=Driven`, `Domains.Materials`(group별 ε/μ/σ/LossTan),
  `Boundaries.LumpedPort`×2(tx/rx, Z₀=50Ω, edge group), `Boundaries.Absorbing`(외곽),
  `Solver.Device=GPU`, 단일 주파수 6.78 MHz.
- 단위 변환 mm→m, port 방향(edge_vertices_xyz 쌍 → terminal 방향).

### B.3 solve + post (`solver/pfsolver/src/pfsolver/solve.py`, `post.py`)
- **도커 forked Palace 엔진 CLI 호출**. pfsolver는 Python API로 호출되지만, Palace 엔진 경계는
  `docker run ... palace <config.json>` JSON/CSV 계약이다. in-process/linking 금지.
- post: S→Z(Z₀ 정규화)와 V/I→Z 두 경로 계산 → 일치 확인 → `network.csv`.
- 부호 고정: Z12/Z21을 HFSS port current 방향 기준으로.

### B.4 출력 스키마 확정 (Phase A에서 미룬 것)
- `em_result.json`, `network.csv`, `derived.csv`, `port_vi.csv`, `solver_manifest.json`
  최소형 emit. (loss/field는 Phase D/E.)

### B.5 acceptance
- [ ] minimal two-port: S/Z shape 2×2·단위·상반성(Z=Zᵀ) 정확.
- [ ] S→Z와 V/I→Z 두 경로 tight 일치(부호 포함).
- [ ] 저복잡도 L/R가 mesh refine 후 HFSS 기준 tolerance 내 수렴(있으면).
- [ ] Z12/Z21 부호가 HFSS와 동일.

---

## Phase C — CUDA-mandatory 런처 + 4-core MPI

> 목표: `pfsolver.solve_bundle`를 실제 운영 경로로. GPU 강제·VRAM 적응·OOM 흡수·telemetry.
> (Phase B가 "경로 관통"이면 C는 "운영 가능·재현 가능"으로 굳히는 단계.)

### C.1 GPU 게이트 (doctor 로직 재사용)
- solve 진입 시 `cuda_probe` 디바이스≥1 확인, 없으면 exception(폴백 없음).
- `nvidia-smi`로 free VRAM 조회(or cudaMemGetInfo) → pool 계산 입력.

### C.2 HYPRE Umpire pool 적응
- free VRAM 기반 device/unified/pinned pool 크기 산출
  (phase0 기준: device/unified 512 MiB, pinned 64 MiB; VRAM에 비례 스케일).
- forked Palace에 pool 크기 주입(환경변수/override lib 또는 config 필드).
- acceptance: 8 GB RTX 3070에서 cpw/cylinder 예제가 OOM 없이 완주(phase0 재현).

### C.3 MPI (Palace engine)
- pfsolver Python API가 Docker Palace를 `palace -np 4 <config.json>`로 호출한다.
- pfsolver 자체는 MPI process가 아니다. MPI는 도커 안 Palace 엔진 소유다.
- watchdog(상위 60분 hard-abort 정책과 정합).

### C.4 OOM/대형 문제 흡수
- 단일 주파수 우선; sweep은 주파수 분할 실행.
- mesh가 VRAM 초과 시 분할/감 refine 전략(우선 경고+가이드, 자동화는 후속).

### C.5 telemetry → `solver_manifest.json`
- solver(name=forked-palace, commit), run command, mesh 입력 해시, pool 설정,
  gpu_name·vram, mpi ranks, wall time, 수렴 정보, bundle design_id/provenance.

### C.6 acceptance
- [ ] `pfsolver.solve_bundle(bundle_dir=...)` GPU에서 완주, no-ferrite 단일주파수 → `network.csv` 산출.
- [ ] GPU 없으면 즉시 명확 실패(폴백 없음).
- [ ] manifest에 재현에 필요한 필드 전부.
- [ ] phase0 OOM 케이스가 pool 적응으로 통과.

---

## Phase A–C 종료 시점의 상태
- `pfsolver.inspect_bundle`·`mesh_bundle`·`solve_bundle` 동작, **no-ferrite 단일주파수**에서 forked Palace가
  2-포트 Z를 산출하고 HFSS와 부호/shape/단위 일치.
- 교차검증 문서 §4·§5의 pfsolver 열을 **no-ferrite 행부터** 채우기 시작.
- 다음(D+): SSW 코일 본체, ferrite(= **M-fork 복소 μ 패치** 선행), sweep·SRF·C, loss/field,
  Mode 2 warm-start, Mode 3 label.

## 의존성 추가
- `solver/pfsolver/pyproject.toml`: pydantic, numpy, gmsh Python wheel, pytest, pyright.
- Dockerfile.base는 Palace 엔진 전용이다. pfsolver Python 런타임을 도커 이미지에 넣지 않는다.
