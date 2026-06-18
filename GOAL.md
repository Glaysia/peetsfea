# GOAL — pfsolver가 HFSS와 같은 terminal-network Z를 내게 만들기

이 브랜치(solver)의 목표는 Ansys HFSS를 대체하는 오픈소스 full-wave 솔버 `pfsolver`다.
병렬 스트림(GOAL1/GOAL2)은 종료 — 이 문서 하나로 통일한다.

## 지금까지 (완료)
- `pfsolver`(Python API, `solver/pfsolver`): `inspect_bundle`/`mesh_bundle`/`solve_bundle` 경로 구현. Palace를 `~/.local/bin/palace` 래퍼(컨테이너 CLI, JSON config / CSV)로 호출. pyright strict + pytest 통과.
- Palace `0.16.1pf` 복소 μ(자기손실) 패치: **완료·PASS** ([solver/docs/palace-0.16.1pf-review.md](solver/docs/palace-0.16.1pf-review.md)).
- HFSS no-ferrite 기준값: **완료** — 교차검증 §3.2 채워짐 (`run/hfss_no_ferrite_nonmodel_full/`). 예: Z11 ≈ 0.35 + j243 Ω, Z12 ≈ j6.69 Ω, L1/L2 ≈ 5.70/5.00 µH, k ≈ 0.0294.

## ★ 현재 과제 — pfsolver solve가 HFSS와 안 맞는다 (물리 모델 문제)
Palace solve는 **성공**하지만 **HFSS와 다른 물리 문제를 풀고 있다.** 후처리 부호·GPU/HYPRE 문제 아님.

**증상(rank4):** pfsolver `Z11 ≈ 0.000421 + j4.48e-8 Ω`, `Z12 ≈ 0`.
HFSS no-ferrite는 `Z11 ≈ 0.35 + j243 Ω`, `Z12 ≈ j6.69 Ω`. → **인덕턴스·TX/RX 결합이 거의 사라진 모델**을 푼 것.

### 근본 원인 3가지 (코드 확인됨)
1. **흡수경계를 모든 body 표면에 검** — `solver/pfsolver/src/pfsolver/mesh.py`(~L223): 모든 volume의 boundary surface를 모아 port surface만 빼고 전부 `absorbing_boundary`로 태깅. → 외곽 air box에만 있어야 할 흡수경계가 **copper/FR4/helper body 표면까지** 들어감. 필드가 내부 구조 표면에서 흡수·절단되니 L·결합이 ~0으로 떨어짐.
2. **HFSS non-model helper body를 vacuum domain으로 푼다** — `palace_config.py`가 `tv·tx_region·tx_region_max·rx_region_max`를 eps=1/mu=1 volume material로 넣음. HFSS에선 이들은 construction/non-model(실제 EM 물체 아님). Palace는 **"하나의 외곽 air domain + 실제 FR4/coil + 외곽 boundary"** 로 재구성해야 함.
3. **copper를 HFSS terminal conductor처럼 안 둠** — `palace_config.py`(L38~52)가 copper를 `Conductivity=5.8e7` **volume material**로 넣고, Boundaries엔 PEC/finite-conductivity 경계가 없음. Palace driven/lumped-port 예제는 금속을 보통 **PEC 또는 finite-conductivity boundary**로 둔다. copper volume 내부를 계산영역에 넣으면 port가 저저항 도체에 붙은 다른 회로가 됨.

### 1순위 아님 (배제됨)
- S→Z 후처리: port-S vs port-V 재구성 검증 통과.
- `L0=1e-3`(STEP mm 좌표) 맞음.
- port face 선택: edge midpoint에 가까운 작은 terminal face 잡음 — ok.

### 수정 방향 (Palace geometry를 HFSS처럼 재세팅)
- **helper/non-model body 제거** (tv·tx_region·tx_region_max·rx_region_max는 solve에서 빼기).
- **하나의 enclosing air/vacuum domain** 생성.
- **FR4만 dielectric volume**으로.
- **copper는 PEC(또는 finite-conductivity) boundary**로 태깅 (volume 계산영역에서 제외).
- **absorbing은 외곽 air domain boundary에만**.
- 그 다음 **rank4 재실행** → `Z11/Z22/Z12`가 HFSS 크기대로 올라와야 함.

### Acceptance
- [ ] mesh.py: 흡수경계가 **외곽 air boundary에만** 걸림(내부 body 표면 제외). 태깅 검증 테스트.
- [ ] palace_config: non-model helper body 제외 + 단일 air domain + FR4 dielectric + **copper = PEC/finite-conductivity boundary**.
- [ ] rank4 solve: `Z11 ≈ 0.35+j243`, `Z22 ≈ 0.24+j213`, `Z12 ≈ j6.69` **크기대(order)로** 산출.
- [ ] §3.2 HFSS no-ferrite와 tolerance 내(L/M ±5%, |Z| ±5%, k ±10%, R ±15%) — DoD numeric 게이트.
- [ ] 증거: config JSON + Palace 실행 로그 + network.csv + §4·§5 pfsolver 열 채움.

## Hard Rules (위반 시 미완)
- **CUDA mandatory**, CPU 폴백 없음. **Full-wave(`Driven`) only**. **Fail-fast**.
- **Mock/stub 금지** — Palace 실제 실행 결과만 인정.
- **Palace CLI 계약(JSON config / CSV) 보존**. pfsolver는 **CLI 없는 Python API**.
- **재현성** — `solver_manifest.json`에 palace/pfsolver commit·mesh/config hash·GPU·MPI·pool·design_id.

## 참조
- 물성 SSOT: [solver/data/materials.toml](solver/data/materials.toml)
- HFSS 교차검증(§3.2 채워짐): [docs/solver-vs-hfss-crossvalidation-plan.html](docs/solver-vs-hfss-crossvalidation-plan.html)
- Palace 0.16.1pf material contract: [solver/docs/palace-0.16.1pf-material-contract.md](solver/docs/palace-0.16.1pf-material-contract.md)
- 큰 그림: [cpp-cuda-fem-solver-longterm-plan.html](cpp-cuda-fem-solver-longterm-plan.html) · Phase A–C: [solver/docs/implementation-plan-phase-A-C.md](solver/docs/implementation-plan-phase-A-C.md)
