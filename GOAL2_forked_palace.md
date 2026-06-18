# GOAL 2 — forked Palace 0.16.1 (CUDA 엔진 + 복소 μ 패치) (스트림 B)

병렬 작업 둘 중 **B**. 짝: [GOAL1_pfsolver.md](GOAL1_pfsolver.md)(Python API 오케스트레이터).
이 스트림은 **포크한 Palace를 별도 서브모듈로 개발**한다 — upstream 0.16.0에서 시작해 **0.16.1**로,
**주파수 종속 복소 투자율(자기손실 μ″)**을 추가하는 게 0.16.1의 핵심 기능이다.

## 포크 / 서브모듈 / 버전 (중요)
- 포크 repo: **`github.com/Glaysia/palace`** (awslabs/palace fork).
- 위치: **`solver/palace` git submodule**(`.gitmodules`). `v0.16.1` 태그 = **stock 릴리스 0.16.1**(upstream-동등, 패치 없음).
- **버전 이름 규칙:**
  - **`0.16.1`** = stock 릴리스(포크 패치 없음). 이미지 `palace:0.16.1`. GOAL1이 지금 쓰는 것.
  - **`0.16.1pfs`** = 이 포크가 **만드는** 버전(자기손실 복소 μ 패치 포함). 이미지 `palace:0.16.1pfs`.
- pfsolver(GOAL1)와 **완전히 별도**로 이 서브모듈 안에서 개발한다. 자기손실 패치 commit들이 쌓여 **0.16.1pfs**가 된다.
- 도커는 `solver/palace` 서브모듈 소스를 **in-tree로 빌드**해 바이너리를 만든다(spack 패키지 복사본이 아니라 서브모듈 소스).
- 로컬 stock 0.16.1 실행환경은 `solver/local/`(podman/docker 래퍼)로 이미 제공됨 — GOAL1은 그걸로 no-ferrite 진행.

## 왜 fork인가 (근거)
upstream Palace 0.16.0 material은 `Permeability`(실수 μ)·`Permittivity`·`LossTan`(유전체)·`Conductivity`만 지원
(`config/domains.md` 확인). **페라이트 자기손실 μ″(magnetic loss tangent)·주파수 종속 μ(f)/ε(f)를 넣을 항이 없다.**
HFSS는 `magnetic_loss_tangent` + `pwlx($mu,Freq)`로 모델링. 그래서 0.16.1 포크에서 직접 추가한다(우리가 owns).

## 산출물
- **`peetsfea-palace:dev`** 도커 이미지(`solver/docker/Dockerfile.base`, `build.sh`, `shell.sh`).
  `solver/palace` 서브모듈 소스 in-tree 빌드, `+cuda cuda_arch=86`, HYPRE Umpire pool override(8 GB VRAM 대응).
- `solver/palace`(Glaysia/palace) 0.16.1 커밋들: 복소 μ 패치 + config schema 확장.

## 병렬성 (GOAL1과의 경계)
- **M1(upstream-동등 빌드)을 먼저** 내라 → GOAL1의 Phase C(solve, no-ferrite)가 이걸로 돌아간다(μ 패치 불필요).
- **M-fork(복소 μ 패치)** 는 그 뒤 독립 진행. GOAL1의 no-ferrite 경로를 막지 않는다.
- 절대 규칙: **M-fork가 upstream no-ferrite 거동을 깨지 않을 것**(회귀 == upstream).

## Palace 인터페이스 계약 (GOAL1과 합의 — 깨지면 안 됨)
- **CLI 유지**: `palace <config.json>` → `postpro/port-S.csv`·`port-V.csv`·`port-I.csv`(+field). JSON in / CSV out.
- no-ferrite는 upstream material 키 그대로.
- 자기손실/분산용 **새 config 필드를 정의하고 문서화**(예: `MagneticLossTan` 또는 복소 `Permeability` + per-frequency dataset).
  → 이 스키마를 GOAL1에 전달해야 orchestrator가 ferrite config를 emit할 수 있다.

## 범위
포함: fork 빌드(CUDA 도커) · upstream 동등 회귀 · **복소 μ(자기손실) material 모델 + assembly 항** ·
주파수 종속 μ(f)/ε(f) material · config schema 확장 + 문서.
제외: 오케스트레이션(GOAL1) · ingest/mesh/post(GOAL1) · transformer.

## Hard Rules
- **CUDA-only 빌드.** CPU 빌드/폴백 없음. `cuda_arch`는 타깃 GPU(RTX 3070 → 86).
- **Full-wave(`Driven`) 유지.** 물리 정식화 변경은 자기손실 추가에 한함(변위전류 항 보존).
- **회귀 무파손.** no-ferrite/유전손실/도체 손실 결과가 upstream과 동일(허용오차 내).
- **CLI 계약 보존.** JSON config / CSV 출력 형태 유지(필드 추가만, 깨는 변경 금지).
- **재현성.** 이미지/바이너리에 fork commit·빌드 플래그 기록(orchestrator manifest가 참조).

## 물리 기준값 (단위 검증용)
- 페라이트(MULL12060) @ 6.78 MHz: **μ_r = 135.59 − j0.296** (μ′=135.59, tanδ_m=0.00218 → μ″=μ′·tanδ_m).
  데이터셋(μ′(f)·tanδ_m(f), x축 GHz)은 `solver/data/materials.toml`.
- 검증: 이 복소 μ 주입 시 자기손실이 0이 아니고, ferrite-enabled HFSS의 R/Q/L 방향과 일치(L↑·손실↑).

## Acceptance
M1 — 서브모듈 소스 빌드 (upstream-동등)
- [ ] `solver/palace` 서브모듈 체크아웃(`git submodule update --init`) → `solver/docker/build.sh` → `peetsfea-palace:dev` 빌드 성공(CUDA, cuda_arch=86), 서브모듈 소스 in-tree 빌드.
- [ ] phase0 예제(cylinder/CPW)가 GPU로 port-S.csv 산출(HYPRE pool override로 OOM 없이).
- [ ] no-ferrite/유전 케이스 결과가 upstream Palace와 일치(회귀).

M-fork — 0.16.1pfs: 복소 μ(자기손실) + 분산 material
- [ ] `solver/palace`(Glaysia/palace)에 magnetic loss(μ″)/복소 μ + μ(f)/ε(f) dispersion commit, config schema 확장 + 문서. 이미지 `palace:0.16.1pfs`로 빌드.
- [ ] ferrite μ=135.59−j0.296 단일주파수 solve → 자기손실≠0, HFSS ferrite 방향과 정합(단위 검증).
- [ ] upstream no-ferrite 회귀 무파손 재확인.
- [ ] 새 config 스키마를 GOAL1에 전달(orchestrator emit 가능).

## 완료 증거 패키지 (리뷰 시 제출)
docker build 로그 + 이미지 태그/digest · fork commit · phase0 예제 GPU 실행 stdout + port-S.csv ·
upstream 회귀 비교(no-ferrite 수치 동일) · 복소 μ 단위 검증(μ=135.59−j0.296 → 손실/HFSS 대조) ·
config schema 문서.

## 리뷰가 볼 것
1. **회귀 무파손**(upstream no-ferrite == fork).
2. **CLI/JSON/CSV 계약 보존**(필드 추가만).
3. 복소 μ 물리 검증(μ″ 손실 실재, HFSS 방향 정합).
4. CUDA-only 빌드·재현(commit/flags 기록).
