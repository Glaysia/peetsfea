# GOAL — pfsolver가 HFSS와 같은 terminal-network Z를 내게 만들기

이 브랜치(`solver`)의 목표는 Ansys HFSS를 대체하는 오픈소스 full-wave 솔버 `pfsolver`다. `pfsolver`는 `solver/pfsolver` 아래의 독립 Python API 서브모듈이고, peetsfea-facing CLI는 만들지 않는다. peetsfea는 나중에 Python API를 import/call한다.

## 완료된 기반

- `pfsolver` API: `inspect_bundle()` / `mesh_bundle()` / `solve_bundle()` 구현. Palace 호출은 `~/.local/bin/palace` wrapper를 통한 JSON config / CSV boundary로 유지.
- `pfsolver`에는 CLI 없음. `console_scripts`, `argparse`, `click`, `typer`, `__main__` 경로 없음.
- Palace는 `solver/palace` 아래 별도 서브모듈 포크로 관리. `pfsolver`와 Palace는 서로 다른 서브모듈/리포지토리 경계다.
- 로컬 기본 Palace 런타임은 Docker `peetsfea-palace:0.16.1pfterm01`. `0.16.1` 뒤 suffix는 앞으로 최대 8글자까지 사용한다.
- Docker wrapper는 `--user "$(id -u):$(id -g)"`로 실행해 Palace postpro 산출물이 root-owned로 남지 않는다.
- Palace fork 패치:
  - 복소 μ / magnetic loss material contract.
  - `SurfaceCurrent.Excitation`으로 current source를 excitation별로 분리.
  - `SurfaceCurrent.Current`로 source current amplitude를 config/schema/docs에 명시.
  - `SurfaceFlux Type="Current"` diagnostic.
  - non-rectangular terminal patch에서는 OBB length 대신 direction-projected length를 사용.
- Docker `peetsfea-palace:0.16.1pfterm01` 빌드 완료.
  - image id `sha256:6a2cebf674b21c5af3d5645cfa0575718155d1eaf49ba3d28d4db118017728fe`
  - build info: `fork_version=0.16.1pfterm01`, `cuda_arch=86`, `source_commit=bc8c335b164ce6c7a2542ade6ee65968e68e4816-dirty`
  - `~/.local/bin/palace` wrapper 기본값도 `peetsfea-palace:0.16.1pfterm01`.
- ingest contract:
  - runner copy `input.toml`은 design TOML로 오인하지 않는다.
  - canonical design TOML은 port ledger `design_id`와 같은 `<design_id>.toml`만 허용한다.
- mesh contract:
  - helper/non-model bodies(`tv`, `tx_region`, `tx_region_max`, `rx_region_max`)는 solve domain에서 제거.
  - FR4 + copper만 실제 material volume으로 유지.
  - copper는 3D conductive solve-inside volume. 70 µm trace, 6.78 MHz skin depth ≈25 µm 기준으로 thickness 4 layers.
  - absorbing boundary는 외곽 air box 6면에만 태깅.
  - HFSS `Region_Abs_2000mm`와 같은 2000 mm absolute-offset air domain을 생성. 현재 mesh summary volume `76.5313424536621 m^3`.

## 현재 결론

Palace 실행, Docker/GPU, HYPRE, mesh generation, CSV parsing이 문제가 아니다. 남은 불일치는 **HFSS lumped terminal이 3D conductive copper volume에 주입하는 terminal current path를 Palace boundary formulation으로 아직 재현하지 못한 것**이다.

2026-06-19 추가 확인: generated mesh에서 port physical surfaces `101/102`는 3D copper volume boundary와 공유되지 않는다. MSH 2.2 element adjacency를 확인하면 TX port triangles는 air attr `1` + FR4 attr `11`, RX port triangles는 air attr `1` + FR4 attr `14`에 붙고, copper attrs `12/15`에는 adjacent tetra face가 없다. 즉 현재 port sheet는 **air/FR4 interface sheet**이지 **copper terminal boundary sheet**가 아니다. 이것이 Palace terminal-current 불일치의 직접 원인이다.

2026-06-19 retag 패치 후: `mesh_bundle()`은 port `101/102`를 copper-adjacent terminal faces로 재태깅한다. `run/pfsolver_hfss_fixed_air2000_retag_meshprobe/`에서 TX `101`은 `(air 1, copper 12)`, RX `102`는 `(air 1, copper 15)` face로 확인됐다. 이어 `peetsfea-palace:0.16.1pfmuflen`은 non-rectangular port patch의 projected-length/axis warning을 허용해 rank1 solve를 완주한다. 그러나 current-source와 native LumpedPort 모두 `Z11≈0.0023+j0.000018 Ω`, `Z22≈0.00495+j0.000022 Ω`, `Z12≈0`로 collapse한다. 따라서 단순 copper-adjacent **outer surface patch**는 HFSS terminal cut/current path가 아니다. 다음 단계는 conductor volume을 실제로 끊는 **copper cross-section terminal cut** 또는 그와 등가인 Palace source/current formulation이다.

2026-06-19 `0.16.1pfterm01` 확인: `SurfaceCurrent.Current=1.0` config/schema/docs/operator patch는 빌드와 Python schema validation을 통과했다. 하지만 기하/source 후보 실험은 아직 numeric fail이다. 1 mm overlapped gap sheet는 copper adjacency를 만들지만 SurfaceCurrent/native LumpedPort 모두 GMRES `NaN`; 0.02 mm overlap은 gmsh segmentation fault; copper-only internal tet face cut(TX 4 faces/RX 3 faces)은 Palace가 수렴하지만 `Z11=0.002615+j0.000015 Ω`, `Z22=0.001854+j0.000009 Ω`, `Z12≈0`로 여전히 collapse한다. 따라서 단순 face retag/overlap이 아니라 **source formulation 자체**가 다음 핵심이다.

### 기준 HFSS

현재 가장 깨끗한 no-ferrite 기준 bundle은 `run/hfss_no_ferrite_fixed_full/`이다. 이 디렉터리는 `ssw_scene.step`, `ssw_step_ledger.json`, `ssw_aedt_port_ledger.json`, `coil_making_token.toml`, `<design_id>.toml`, `input.toml`, HFSS reports를 모두 가진다.

HFSS final adaptive pass @ 6.78 MHz:

- `Z11 = 0.279756 + j241.677390 Ω`
- `Z22 = 0.215108 + j214.664641 Ω`
- `Z12 = 0.008852 + j6.488999 Ω`
- `Ltx = 5.673179 µH`, `Lrx = 5.039077 µH`, `M = 0.152324 µH`, `k = 0.028489`

### Palace evidence

1. `run/pfsolver_hfss_fixed_currentsource_rank1/`
   - exact HFSS fixed bundle ingest 성공.
   - current-source contract solve 성공.
   - `surface-I.csv` physical input current: `0.05152105132651 A`.
   - `Z11 = 45.53 + j6380.18 Ω`, `Z22 = 30.72 + j7637.32 Ω`, `Z12 = 2.568 + j238.532 Ω`.
   - `Ltx = 149.77 µH`, `Lrx = 179.28 µH`, `M = 5.599 µH`, `k = 0.03417`.
   - reciprocal하지만 HFSS보다 self/mutual impedance가 26-37배 큼.

2. `run/pfsolver_hfss_fixed_air2000_currentsource_rank1/`
   - HFSS와 같은 2000 mm air region volume으로 solve 완료.
   - postprocess는 fail-fast로 정지: derived `Ltx/Lrx`가 음수.
   - raw `Z = V @ inv(surface-I)`:
     `Z11 = 483.11 - j7705.50 Ω`, `Z22 = 15731.86 - j56602.70 Ω`, `Z12 ≈ -799.35 + j2315.83 Ω`.
   - air margin mismatch만으로 설명되지 않으며 current-source formulation은 더 멀어짐.

3. `run/proto_air2000_lumped_native_rank1/`
   - `SurfaceCurrent` 제거, Palace native `LumpedPort Excitation=1/2`, `Active=true`.
   - S→Z 결과: `Z11 ≈ 45.53 - j0.265 Ω`, `Z22 ≈ 39.58 - j0.015 Ω`, `Z12 ≈ -3.1e-5 - j0.0099 Ω`.
   - native lumped port도 3D copper loop terminal current를 HFSS처럼 구동하지 못한다.

4. `run/pfsolver_hfss_fixed_air2000_retag_pfmuflen2_currentsource_rank1/`
   - port `101/102`를 copper-adjacent face로 retag, Docker `peetsfea-palace:0.16.1pfmuflen`, rank1.
   - Palace solve exit 0, GMRES converged, wall time `141.6 s`, Palace total `125.4 s`, peak HWM `3.6 GB`.
   - `Z11 = 0.002305 + j0.000018 Ω`, `Z22 = 0.004947 + j0.000022 Ω`, `Z12 ≈ 0`.
   - 실행/태깅은 해결됐지만 terminal current path가 local surface patch로 collapse한다.

5. `run/proto_air2000_retag_pfmuflen_lumped_native_rank1/`
   - 같은 retag mesh에서 `SurfaceCurrent` 제거, native `LumpedPort Active=true`.
   - S→Z 결과도 `Z11 = 0.002305 + j0.000018 Ω`, `Z22 = 0.004947 + j0.000022 Ω`, `Z12≈0`.
   - current-source만의 문제가 아니라 Palace lumped terminal boundary 자체가 현재 retag patch로는 HFSS terminal cut을 재현하지 못한다.

6. `run/proto_internal_copper_cut_currentsource_rank1/`
   - port `101/102`를 copper-only internal tet faces로만 구성(TX 4 faces/RX 3 faces), Docker `peetsfea-palace:0.16.1pfterm01`, rank1.
   - Palace solve exit 0, excitation별 GMRES 15 iterations, wall total `122.9 s`, peak HWM `3.6 GB`.
   - `Z11 = 0.002615 + j0.000015 Ω`, `Z22 = 0.001854 + j0.000009 Ω`, `Z12≈0`.
   - `port-I-field.csv` 기준 diagnostic도 `Z11≈0.012+j0.534 Ω`, `Z22≈0.012+j0.581 Ω`, `Z12≈0`라 HFSS order가 아니다.
   - internal cut face 자체도 loop terminal current를 만들지 못한다.

### 배제한 가설

- Docker vs Podman: Docker로 정상 실행하며 권한도 해결됨.
- stock vs patched Palace 동작 여부: patched Docker image로 `--version`, rank1 solves, CSV 산출 확인.
- `surface-I.csv` 단위 해석: Palace 소스상 `0.051521 A`는 dimensionalized physical current가 맞다. 숨은 1 A로 재해석하면 안 된다.
- `port-I.csv`를 terminal current로 쓰는 방법: `V @ inv(port-I)`는 50 Ω matched branch만 재구성한다. terminal conductor current가 아니다.
- air-domain 200 mm mismatch 단독 원인: 2000 mm로 HFSS region을 맞춰도 numeric parity는 개선되지 않았다.
- overlapped gap sheet 단독 원인: 1 mm overlap은 Palace `NaN`, 0.02 mm overlap은 gmsh segfault.
- copper-only internal tet face retag: 수렴하지만 mΩ collapse라 source formulation 문제를 배제하지 못한다.

## 남은 핵심 작업

- `101/102` copper-adjacent outer-surface retag는 완료됐지만 acceptance 불가다. HFSS terminal은 local surface patch가 아니라 conductor current path를 끊어 구동한다.
- `network_field.csv`는 Palace field-power/current diagnostic으로 산출하지만 acceptance 전류는 아니다. 현재 field-current 기준도 HFSS order에 들어오지 않는다.
- port sheet 생성/fragment를 고쳐 physical surfaces `101/102`가 **copper cross-section terminal cut** 또는 그와 등가인 내부 conductor terminal boundary가 되게 만든다.
- HFSS lumped terminal sheet와 등가인 Palace boundary를 재정의:
  - 현재 air-domain internal sheet source나 copper outer surface source가 아니라, 3D copper terminal cut/current path에 결합되는 formulation이어야 한다.
  - 필요하면 Palace fork에 terminal-current postprocess/source term을 추가한다.
- 그 후 `solve_bundle()` acceptance postprocess를 확정:
  - `stock port-I.csv`는 terminal current로 사용 금지.
  - `surface-I.csv` 또는 새 Palace CSV가 HFSS terminal current와 동등하다는 소스/수치 증거가 있어야 함.
- rank1 diagnostic이 HFSS order에 들어온 뒤 rank4 acceptance 실행.
- numeric gate 통과 후 Palace field output으로 air-gap E/H 또는 B-field plot 이미지를 `docs/solver-vs-hfss-crossvalidation-plan.html`에 실제 이미지로 첨부.

## Acceptance

- [x] 독립 `solver/pfsolver` Python API. CLI 없음.
- [x] Palace 별도 `solver/palace` 서브모듈 포크.
- [x] Docker default runtime `peetsfea-palace:0.16.1pfterm01`.
- [x] runner `input.toml` 동반 bundle ingest.
- [x] helper/non-model 제거 + 단일 air domain + 외곽 absorbing only.
- [x] HFSS 2000 mm radiation region volume 재현.
- [x] 3D copper solve-inside + skin-depth mesh policy.
- [x] 현재 port sheet가 copper가 아니라 air/FR4 interface에 붙어 있음을 MSH adjacency로 확인.
- [x] port physical group 101/102를 copper-adjacent outer surface로 retag하고 Palace rank1 완주.
- [x] `SurfaceCurrent.Current` config/schema/operator patch + Docker `0.16.1pfterm01` 빌드.
- [ ] port physical group 101/102를 HFSS-equivalent copper cross-section terminal cut/current path로 재정의.
- [ ] Palace terminal source/current formulation이 HFSS lumped terminal과 동등함을 증명.
- [ ] rank4 solve: `Z11/Z22/Z12`가 HFSS 크기대(order)로 산출.
- [ ] HFSS no-ferrite tolerance: L/M ±5%, |Z| ±5%, k ±10%, R ±15%.
- [ ] 증거: config JSON + Palace 실행 로그 + network.csv + solver_manifest.json + HTML 표 갱신.
- [ ] 성공 run field plot image를 HTML에 첨부.

## Hard Rules

- CUDA mandatory, CPU fallback 없음.
- Full-wave Palace `Driven` only.
- Mock/stub 결과 금지. 실제 Palace 실행만 인정.
- Fail-fast. 실패를 로그만 남기고 계속 진행하지 않는다.
- copper를 2D boundary로 접지 않는다. 70 µm trace에서 skin depth가 약 25 µm라 3D가 필수다.
- `solver_manifest.json`에는 palace/pfsolver commit, container runtime/image, mesh/config hash, GPU, MPI, pool, design_id를 남긴다.

## 참조

- 물성 SSOT: [solver/data/materials.toml](solver/data/materials.toml)
- HFSS 교차검증: [docs/solver-vs-hfss-crossvalidation-plan.html](docs/solver-vs-hfss-crossvalidation-plan.html)
- Palace material contract: [solver/docs/palace-0.16.1pf-material-contract.md](solver/docs/palace-0.16.1pf-material-contract.md)
- Phase A-C: [solver/docs/implementation-plan-phase-A-C.md](solver/docs/implementation-plan-phase-A-C.md)
