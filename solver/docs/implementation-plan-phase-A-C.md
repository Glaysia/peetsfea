# pfsolver — Phase A–C 구체 구현 계획

목적: `pfsolver`가 Ansys 없이 0.3.7 STEP 번들을 받아 HFSS terminal-network Z(f)를
재현하는 경로의 **첫 세 단계**를 task/struct/acceptance 수준까지 구체화한다.

- 상위 문서: [`../../cpp-cuda-fem-solver-longterm-plan.html`](../../cpp-cuda-fem-solver-longterm-plan.html)
  (§6 파이프라인·§11 로드맵), 교차검증 [`../../docs/solver-vs-hfss-crossvalidation-plan.html`](../../docs/solver-vs-hfss-crossvalidation-plan.html)
- 이미 완료: **M0** — Docker 전용 빌드 + `pfsolver doctor`(CUDA 게이트). 본 계획은 그 위.
- 코어: **forked Palace** `Driven`(full-wave). CUDA mandatory, 4-core MPI, CPU 폴백 없음.

CLI 최종형: `pfsolver {version|doctor|inspect|mesh|solve} <bundle_dir>`.
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

## Phase A — `pfsolver inspect` + 출력 스키마

> 목표: "HFSS 없이 setup을 구성할 수 있다"를 증명. 번들을 읽어 solve에 필요한
> 모든 정보를 내부 모델로 복원하고, 누락이면 fail. **출력 스키마는 solve와 함께
> 확정하므로 여기서는 read-side 모델 + `inspect` dump까지.**

### A.1 파서 (`src/ingest/`)
- `step_bundle.{hpp,cpp}` — `<bundle_dir>` 존재/파일 5종 확인, 경로 해석.
- `ledger.cpp` — `ssw_step_ledger.json` → `std::vector<Body>` + name 분류 집합.
- `port_ledger.cpp` — `ssw_aedt_port_ledger.json` → `std::vector<PortEdge>`.
- `design_toml.cpp` — `<design_id>.toml` → `FreqPlan` + ferrite enable + material 매핑.
- `materials.cpp` — `solver/data/materials.toml` → `MaterialDB`.
- JSON: nlohmann/json, TOML: toml++ (둘 다 header-only, Dockerfile.base에 추가).

### A.2 내부 모델 (`src/model/scene.hpp`)
```cpp
enum class Role { Copper, Fr4, Ferrite, NonModel };
struct Body { std::string id; Role role; std::string material;
              std::array<double,3> center_mm, size_mm; };
struct PortEdge { std::string role;            // "tx" | "rx"
                  std::string copper_body;     // owning conductor
                  std::array<std::array<double,3>,2> seg_a, seg_b; }; // edge_vertices_xyz 쌍
struct Material { double eps_r, mu_r_re, mu_r_im, sigma, tan_d_e, tan_d_m; bool dispersive; };
struct FreqPlan { double f0_hz=6.78e6; double sweep_start_hz, sweep_end_hz; int sweep_count; bool single; };
struct Excitation { std::string port; double volt_mag; double phase_deg; }; // TX 100V@0, RX 100V@90
struct Scene { std::vector<Body> bodies; std::vector<PortEdge> ports;
               MaterialDB materials; FreqPlan freq; std::vector<Excitation> sources;
               bool ferrite_enabled; std::string design_id, units; };
```

### A.3 복원 + 검증 규칙 (fail-fast)
- body role과 `*_body_names` 교차검증 → 불일치 fail.
- `port_edges`가 정확히 tx 1 + rx 1, 각 edge가 copper body에 귀속 → 아니면 fail.
- 각 port의 copper_body가 `copper_body_names`에 존재 → 아니면 fail.
- ferrite_enabled=true인데 ferrite body 없음(또는 반대) → fail.
- 모든 material 참조가 `MaterialDB`에 존재 → 아니면 fail.
- units != "mm" → fail.

### A.4 `inspect` 출력
- stdout 사람용 요약 + `--json`이면 `inspect.json`(body count·roles, port 쌍 좌표,
  freq plan, material 표, ferrite flag). 이게 Phase B의 fixture 입력.

### A.5 acceptance
- [ ] `pfsolver inspect run/ssw_0_3_0_fixed` → exit 0, body 11/copper 2/fr4 4/ferrite 1, port tx·rx 각 1.
- [ ] 일부러 파일 1개 지우면 → 명확한 메시지로 exit≠0.
- [ ] `--json` 출력이 §A.2 모델을 빠짐없이 직렬화.
- [ ] 단위테스트: fixed 번들 fixture로 파서별 골든값 비교.

---

## Phase B — minimal two-port cross-solver check (V0)

> 목표: 가장 단순한 2-포트(코일 아님, copper pad/loop)로 ingest→mesh→solve→Z
> 전 경로를 처음 관통시키고 HFSS와 **부호·shape·단위**를 맞춘다. SSW 코일·ferrite는 아직.

### B.1 메시 (`pfsolver mesh`, `src/mesh/`)
- gmsh C++ API로 `ssw_scene.step`(또는 minimal STEP) import(OCCT).
- physical group 부여: 각 Body→domain group, port edge→port group, 외곽 vacuum→boundary.
- copper edge·port gap refine, 출력 `mesh.msh`(Palace 호환 포맷) + `mesh_tags.json`(group↔role).
- acceptance: group 수·태깅이 `inspect` 모델과 1:1, gmsh 무에러.

### B.2 config emit (`src/assemble/palace_config.cpp`)
- `Scene` + mesh tags → forked Palace `Driven` config(JSON):
  `Problem.Type=Driven`, `Domains.Materials`(group별 ε/μ/σ/LossTan),
  `Boundaries.LumpedPort`×2(tx/rx, Z₀=50Ω, edge group), `Boundaries.Absorbing`(외곽),
  `Solver.Device=GPU`, 단일 주파수 6.78 MHz.
- 단위 변환 mm→m, port 방향(edge_vertices_xyz 쌍 → terminal 방향).

### B.3 solve + post (`src/solve/`, `src/post/`)
- forked Palace 실행(MPI 4) → `postpro/port-S.csv`·`port-V.csv`·`port-I.csv`.
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

> 목표: `pfsolver solve`를 실제 운영 경로로. GPU 강제·VRAM 적응·OOM 흡수·telemetry.
> (Phase B가 "경로 관통"이면 C는 "운영 가능·재현 가능"으로 굳히는 단계.)

### C.1 GPU 게이트 (doctor 로직 재사용)
- solve 진입 시 `cuda_probe` 디바이스≥1 확인, 없으면 exit≠0(폴백 없음).
- `nvidia-smi`로 free VRAM 조회(or cudaMemGetInfo) → pool 계산 입력.

### C.2 HYPRE Umpire pool 적응
- free VRAM 기반 device/unified/pinned pool 크기 산출
  (phase0 기준: device/unified 512 MiB, pinned 64 MiB; VRAM에 비례 스케일).
- forked Palace에 pool 크기 주입(환경변수/override lib 또는 config 필드).
- acceptance: 8 GB RTX 3070에서 cpw/cylinder 예제가 OOM 없이 완주(phase0 재현).

### C.3 MPI launch
- `palace -np 4`(4-core 고정) wrapper, stdout/stderr 캡처, 종료코드 전파.
- watchdog(상위 60분 hard-abort 정책과 정합).

### C.4 OOM/대형 문제 흡수
- 단일 주파수 우선; sweep은 주파수 분할 실행.
- mesh가 VRAM 초과 시 분할/감 refine 전략(우선 경고+가이드, 자동화는 후속).

### C.5 telemetry → `solver_manifest.json`
- solver(name=forked-palace, commit), run command, mesh 입력 해시, pool 설정,
  gpu_name·vram, mpi ranks, wall time, 수렴 정보, bundle design_id/provenance.

### C.6 acceptance
- [ ] `pfsolver solve <bundle>` GPU에서 완주, no-ferrite 단일주파수 → `network.csv` 산출.
- [ ] GPU 없으면 즉시 명확 실패(폴백 없음).
- [ ] manifest에 재현에 필요한 필드 전부.
- [ ] phase0 OOM 케이스가 pool 적응으로 통과.

---

## Phase A–C 종료 시점의 상태
- `pfsolver inspect|mesh|solve` 동작, **no-ferrite 단일주파수**에서 forked Palace가
  2-포트 Z를 산출하고 HFSS와 부호/shape/단위 일치.
- 교차검증 문서 §4·§5의 pfsolver 열을 **no-ferrite 행부터** 채우기 시작.
- 다음(D+): SSW 코일 본체, ferrite(= **M-fork 복소 μ 패치** 선행), sweep·SRF·C, loss/field,
  Mode 2 warm-start, Mode 3 label.

## 의존성 추가 (Dockerfile.base)
- nlohmann/json, toml++ (header-only)
- gmsh (이미 계획됨, OCCT 포함) — C++ API 링크
- forked Palace(M1) + CUDA + MPI
