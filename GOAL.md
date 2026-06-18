# GOAL — solver 브랜치: HFSS 없이 `pfsolver`로 terminal-network Z(f) 재현

이 브랜치(solver)의 목표는 Ansys HFSS를 대체하는 오픈소스 full-wave 솔버 `pfsolver`다.
작업은 **병렬 두 스트림**으로 나뉘어 각각 에이전트에게 뿌린다. **이 문서는 두 스트림을 관장하는 인덱스**다 —
스트림별 상세(범위·Hard Rules·Acceptance·증거)는 각 GOAL 파일에 있다.

## 두 스트림
- **[GOAL1_pfsolver.md](GOAL1_pfsolver.md)** — `solver/pfsolver` 독립 Python API 서브프로젝트.
  peetsfea가 나중에 Python API로 호출할 `inspect_bundle`/`mesh_bundle`/`solve_bundle` 표면을 제공하고,
  no-ferrite 단일주파수에서 Palace wrapper(`~/.local/bin/palace`)를 호출해 Z(f)를 산출한다.
  HFSS no-ferrite 기준값 생성(§3.2)도 이 스트림.
- **[GOAL2_forked_palace.md](GOAL2_forked_palace.md)** — Palace fork: CUDA 도커 엔진(`peetsfea-palace:dev`) + 주파수 종속 복소 μ(자기손실) 패치.

## 아키텍처 (pyaedt → ansysedt 구도)
- `pfsolver` = **독립 Python API 서브프로젝트**(`solver/pfsolver`, pyright strict + pydantic), 도커 밖.
- peetsfea-facing CLI는 만들지 않는다. peetsfea는 나중에 `pfsolver` Python API를 import/call한다.
- **컨테이너 = Palace 엔진만**(CUDA C++). C++은 Palace 포크 안에만, 오케스트레이터엔 없음.
- `pfsolver`와 Palace 엔진의 경계만 **Palace wrapper CLI(JSON config / CSV)** 다. 로컬 기본은 `~/.local/bin/palace <config.json>`이고, 래퍼가 컨테이너와 `mpirun -np 4 palace`를 소유한다. Palace엔 stable libpalace 없음 → 이 내부 엔진 호출이 안정 계약.

## 병렬성 (두 스트림이 어떻게 안 막히나)
- GOAL1 Phase A(inspect)·B(mesh/config)는 Palace solve 불필요 → GOAL2와 **완전 병렬**.
- GOAL1 Phase C(solve)는 GOAL2 **M1(upstream-동등 빌드)** 이면 충분(μ 패치 불필요, no-ferrite).
- **ferrite(복소 μ)** 만 GOAL2 M-fork에 의존 → 이번 push 밖.
- 동기점: GOAL2가 자기손실 **config schema**를 정의 → GOAL1에 전달(ferrite 때 orchestrator가 emit).

## 모드 로드맵 (이 push = Mode 1 / no-ferrite)
- Mode 1 = FEM(지금). → 데이터셋 축적 → transformer는 **다른 프로젝트**에서 학습/배포.
- Mode 2/3 = pfsolver에서 **추론만**.

## Sweep 모델
HFSS terminal처럼 **단일 주파수에서 메시 확정 → 같은 메시로 다주파수 sweep**(재적응 안 함; Palace `Driven` native).
이번 push는 단일 주파수만.

## 작업 방식 / 검수
- 구현은 에이전트들이 각 GOAL을 따라 **병렬** 진행.
- Claude(나)는 1시간마다 호출되어 **각 스트림의 Acceptance/Hard Rules 기준으로 검수**(코드 안 짬, 증거 요구).
- "완료"는 주장 아니라 각 GOAL의 **완료 증거 패키지**로 증명. mock/stub·silent degrade·CPU 폴백·Python API/Palace JSON-CSV 계약 파손은 미완.
- 공통 강조: ① 실제 Palace run 증거 ② 아키텍처 경계(`solver/pfsolver`=Python API / 컨테이너 안=Palace 엔진만) ③ no-ferrite↔ferrite 경계 ④ Palace JSON/CSV 계약 보존 ⑤ manifest 재현성.

## 공통 기준값 / 참조
- 물성 SSOT: [solver/data/materials.toml](solver/data/materials.toml) (copper σ=5.8e7, FR4 εr 4.4/tanδ 0.02, ferrite μ=135.59−j0.296 등).
- HFSS 교차검증: [docs/solver-vs-hfss-crossvalidation-plan.html](docs/solver-vs-hfss-crossvalidation-plan.html) (no-ferrite §3.2는 GOAL1 선행 task로 채움).
- 큰 그림: [cpp-cuda-fem-solver-longterm-plan.html](cpp-cuda-fem-solver-longterm-plan.html) · Phase A–C 상세: [solver/docs/implementation-plan-phase-A-C.md](solver/docs/implementation-plan-phase-A-C.md).
