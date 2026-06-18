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

2026-06-19 추가 확인: generated mesh에서 port physical surfaces `101/102`의 triangle face adjacency는 TX `(air 1, FR4 11)`, RX `(air 1, FR4 14)`로 남는다. 이것 자체는 HFSS-style feed-gap sheet에서는 정상일 수 있다. 진짜 불변조건은 face adjacency가 아니라 **port sheet의 긴 두 변이 import된 copper body의 실제 terminal edge curve 두 개를 재사용하는지**다.

2026-06-19 retag 패치 후: `mesh_bundle()`은 port `101/102`를 copper-adjacent terminal faces로 재태깅한다. `run/pfsolver_hfss_fixed_air2000_retag_meshprobe/`에서 TX `101`은 `(air 1, copper 12)`, RX `102`는 `(air 1, copper 15)` face로 확인됐다. 이어 `peetsfea-palace:0.16.1pfmuflen`은 non-rectangular port patch의 projected-length/axis warning을 허용해 rank1 solve를 완주한다. 그러나 current-source와 native LumpedPort 모두 `Z11≈0.0023+j0.000018 Ω`, `Z22≈0.00495+j0.000022 Ω`, `Z12≈0`로 collapse한다. 따라서 단순 copper-adjacent **outer surface patch**는 HFSS feed-gap terminal current path가 아니다.

2026-06-19 `0.16.1pfterm01` 확인: `SurfaceCurrent.Current=1.0` config/schema/docs/operator patch는 빌드와 Python schema validation을 통과했다. 하지만 기하/source 후보 실험은 아직 numeric fail이다. 1 mm overlapped gap sheet는 copper adjacency를 만들지만 SurfaceCurrent/native LumpedPort 모두 GMRES `NaN`; 0.02 mm overlap은 gmsh segmentation fault; copper-only internal tet face cut(TX 4 faces/RX 3 faces)은 Palace가 수렴하지만 `Z11=0.002615+j0.000015 Ω`, `Z22=0.001854+j0.000009 Ω`, `Z12≈0`로 여전히 collapse한다. 따라서 단순 face retag/overlap이 아니라 **peetsfea/HFSS와 같은 feed-gap edge topology + Palace source formulation**이 다음 핵심이다.

2026-06-19 semantic edge patch: `pfsolver.mesh_bundle()`은 이제 peetsfea `ssw_ports.py`와 같은 규칙을 따른다. `ssw_aedt_port_ledger.json`의 `edge_vertices_xyz` 두 개를 `port.copper_body_name`의 imported Gmsh/OCC copper boundary curves에 `1e-5 mm` tolerance로 resolve하고, 새 endpoint point를 만들지 않는다. 실제 clean bundle에서 TX는 copper curves `(372, 205)`, RX는 `(692, 530)`으로 정확히 resolve된다. port sheet는 이 copper curves 두 개 + 새 connector line 두 개로 구성하고, surface boundary가 그 네 curve를 유지하지 않으면 fail-fast한다. STEP 시각화 PNG:
- `run/pfsolver_port_visual_debug/semantic_tx_port_step_plane2d.png`
- `run/pfsolver_port_visual_debug/semantic_rx_port_step_plane2d.png`
- `run/pfsolver_port_visual_debug/semantic_tx_port_step_3d.png`
- `run/pfsolver_port_visual_debug/semantic_rx_port_step_3d.png`
보고서 추적 asset:
- `docs/assets/solver-port-visual/tx_feed_gap_step_plane2d.png`
- `docs/assets/solver-port-visual/rx_feed_gap_step_plane2d.png`
- `docs/assets/solver-port-visual/tx_feed_gap_step_3d.png`
- `docs/assets/solver-port-visual/rx_feed_gap_step_3d.png`

2026-06-19 semantic edge rank1: `run/pfsolver_hfss_fixed_semantic_edge_lumped_rank1/`에서 Docker `peetsfea-palace:0.16.1pfterm01`, 4-rank GPU solve가 정상 수렴했다(GMRES 14/15 iterations, Palace total `84.8 s`, peak HWM `4.5 GB`). 하지만 postprocess는 `surface-F` terminal flux-current Z 비상반성으로 fail-fast했다. Raw diagnostic:
- `S→Z`: `Z11=45.5285−j0.2659 Ω`, `Z22=39.5760−j0.0158 Ω`, `Z12≈−j0.00984 Ω`
- `V @ inv(surface-F)`: negative self L, nonreciprocal (`Z12≈5.69+j203.74 Ω`, `Z21≈−20.31−j1660.72 Ω`)
- `V @ inv(port-I-field)`: negative self L, nonreciprocal

따라서 **peetsfea/HFSS edge topology는 이제 맞지만, Palace native `LumpedPort`/current diagnostic이 HFSS terminal conductor current를 만들지 못한다**. 다음 핵심은 Palace 쪽 terminal source/current formulation이다.

2026-06-19 semantic edge + SurfaceCurrent 재시도: 같은 semantic feed-gap sheet에 native `LumpedPort` 대신 patched `SurfaceCurrent(Current=1.0, Excitation=1/2)`를 걸어 `run/proto_semantic_edge_surfacecurrent_rank1/`에서 다시 실행했다. Palace는 정상 수렴했다(Palace total `92.7 s`, peak HWM `4.5 GB`). `I_inc=0.051521 A` 기준 `Z=V @ inv(I_inc)`:
- `Z11=484.34−j7684.19 Ω`
- `Z22=15186.40−j55850.61 Ω`
- `Z12≈Z21=−772.01+j2276.05 Ω`

상반성은 맞지만 self inductance가 음수라 acceptance 불가다. 즉 coordinate-copy 문제가 아니라, Palace의 sheet source가 HFSS terminal conductor current와 등가가 아니다.

## ★ Claude 진단 (2026-06-19)

**full-wave 맞다.** pfsolver config는 `Problem.Type="Driven"` = 완전 Maxwell 주파수영역 = full-wave(코드+생성 config 확인). HFSS도 같은 full-wave terminal로 이 코일에서 j243Ω를 내므로 full-wave로 **가능한** 문제다.

**1순위 원인 — port가 코일 루프 전류를 안 만든다 (topology):**
`port_edges`는 코일 두 터미널 패드 사이 **~2.1 mm 급전 간극(feed gap)**의 두 모서리(seg A, seg B)다(실측: TX gap 2.10 mm, RX 2.19 mm). HFSS lumped terminal은 **이 간극을 채우는 sheet**에 걸려 전류를 한 패드→스파이럴 전체 한 바퀴→다른 패드로 돌린다 → 자기인덕턴스 j243 Ω.
- 코일은 **이미 두 끝이 2.1 mm 떨어진 열린 스파이럴**이다. **copper를 새로 끊지 마라**(internal tet cut 시도들이 틀린 이유). 이미 존재하는 간극을 port sheet로 채우고 두 끝면(터미널 단면)을 전극으로 쓴다.
- Codex 변형이 전부 같은 식으로 실패한 이유: copper 외부 표면 패치·내부 단면 cut → 전류가 루프를 안 돌고 국소 단락 → `Z11≈mΩ, Z12≈0` 붕괴. overlap sheet → degenerate → NaN/segfault. 작은 air + current-source → 국소 과대 → 26~37배 overshoot. **collapse와 overshoot는 같은 뿌리**(전류가 스파이럴 루프가 아님)다.
- 수정: port sheet = **2.1 mm 간극을 채우는 사각면**(두 변 = imported copper curve로 resolve한 seg A·seg B, 각각 copper 터미널 단면에 접함), excitation = 간극 가로지르는 방향, native `LumpedPort`. copper face / 내부 cut / overlap 아님.
- copper 3D solve-inside(skin depth)는 **그대로 유지** — R용이고 인덕턴스 붕괴 원인 아님.

**2순위 — full-wave의 저주파 한계 (port 고친 뒤 볼 것):**
6.78 MHz에서 코일은 전기적으로 매우 작다(λ≈44 m ≫ 0.3 m). full-wave curl-curl은 ω→0에서 ill-conditioned(low-frequency breakdown)다. Palace `Driven`은 본래 GHz(qubit/cavity)용이라 이 극저주파·전기적-소형 영역은 Palace의 비주류 regime이다. port를 고쳐도 L이 노이지/부정확하면 그땐 **저주파 안정화**(element order↑, gauge, 적절한 Palace 설정)가 다음 변수다. 단, 현재의 완전 붕괴(Z12=0)는 저주파보다 **port topology가 1순위**임을 가리킨다.

**rings 예제 주의:** Palace `rings`는 **Magnetostatic(= full-wave 아님)**이다. "루프 전류 + flux로 L 추출" 개념의 **캘리브레이션 참고**로만 쓰고 제품 formulation으로 채택 금지(full-wave 규칙 위반).

**프로세스:** Phase B(단순 1-loop 코일 + 간극 1개)를 건너뛰고 전체 SSW 스파이럴에서 brute-force 중이다. **최소 1-loop 코일로 회귀해 feed-gap lumped port 정의를 못 박고 → SSW로 확대**하라. 전체 형상에서 port 위상 디버깅 금지.

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
   - current-source만의 문제가 아니라 Palace lumped terminal boundary 자체가 현재 retag patch로는 HFSS feed-gap terminal을 재현하지 못한다.

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

- `101/102` copper-adjacent outer-surface retag는 폐기한다. HFSS terminal은 local surface patch나 내부 cut이 아니라, 이미 열린 스파이럴의 feed-gap edge pair를 terminal sheet로 잇는다.
- `101/102` port sheet 생성은 이제 peetsfea/HFSS 규칙처럼 실제 imported copper edge curve 두 개를 resolve해서 만든다. 이 topology에서도 Palace native `LumpedPort`는 HFSS terminal loop current를 만들지 못했다.
- `network_field.csv`는 Palace field-power/current diagnostic으로 산출하지만 acceptance 전류는 아니다. 현재 field-current 기준도 HFSS order에 들어오지 않는다.
- HFSS lumped terminal sheet와 등가인 Palace boundary를 재정의:
  - 현재 copper outer surface source나 내부 cut이 아니라, feed-gap sheet topology에서 3D copper terminal current path에 결합되는 formulation이어야 한다.
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
- [x] 초기 좌표복사 port sheet가 peetsfea/HFSS edge-resolve 규칙을 따르지 않음을 STEP/MSH 시각화로 확인.
- [x] port physical group 101/102를 copper-adjacent outer surface로 retag하고 Palace rank1 완주.
- [x] `SurfaceCurrent.Current` config/schema/operator patch + Docker `0.16.1pfterm01` 빌드.
- [x] port physical group 101/102를 imported copper edge curves `(TX 372/205, RX 692/530)` 기반 feed-gap sheet로 재정의.
- [x] semantic feed-gap sheet mesh에서 Palace native `LumpedPort` rank1 diagnostic 실행.
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
