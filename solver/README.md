# pfsolver — open-source full-wave FEM solver (HFSS replacement)

HFSS를 대체해 0.3.7 STEP 번들에서 terminal-network Z(f)를 산출한다.

## 아키텍처 (pyaedt → ansysedt 구도)
- **pfsolver = Python 오케스트레이터** (pyright strict + pydantic). peetsfea 생태계 안, **도커 밖**.
  번들 ingest → gmsh(Python) 메시 → Palace config emit → **도커 forked Palace를 CLI 호출** → CSV→Z → manifest.
- **Docker = forked Palace 엔진만** (`peetsfea-palace:dev`, CUDA C++). 유일하게 컨테이너화되는 것.
- **C++은 forked Palace 안에만** (주파수 종속 복소 μ 패치). 오케스트레이터엔 C++ 없음.
- 안정 인터페이스 = **CLI(JSON config / CSV)**. Palace엔 stable 공개 libpalace 없음.

## 모드
- **Mode 1 = FEM** (지금 구축). 정밀 Z(f).
- Mode 1로 데이터셋 축적 → transformer는 **다른 프로젝트**에서 학습/배포.
- **Mode 2/3 = 추론만** (pfsolver가 배포 모델 호출). 학습 안 함.

## Sweep 모델
HFSS terminal처럼 **단일 주파수에서 메시 확정 → 같은 메시로 다주파수 sweep**(주파수마다 재적응하는 진짜 sweep은 자원 과다라 안 함). Palace `Driven`의 native 동작과 일치.

## 디렉토리
```
solver/
  data/materials.toml          # 물성 SSOT (AEDT 라이브 + 소스 확인값)
  docker/
    Dockerfile.base            # forked Palace CUDA 엔진 이미지
    build.sh                   # docker build -> peetsfea-palace:dev
    shell.sh                   # GPU 붙은 dev 컨테이너 셸 (포크 빌드/palace 실행)
  docs/implementation-plan-phase-A-C.md
```
Python 오케스트레이터 코드 위치/패키징은 구현 시 확정(peetsfea 생태계).

## Palace 엔진 도커
```bash
cd solver
./docker/build.sh          # peetsfea-palace:dev 빌드 (heavy, 1회)
./docker/shell.sh          # GPU 붙은 셸로 진입 (포크 패치/빌드, palace 실행)
```
CUDA mandatory: 이미지는 CUDA-only 빌드. 오케스트레이터가 invoke 전 GPU 게이트(no CPU fallback).

## 상세
- 목표/Acceptance: [../GOAL.md](../GOAL.md)
- Phase A–C 계획: [docs/implementation-plan-phase-A-C.md](docs/implementation-plan-phase-A-C.md)
- 교차검증: [../docs/solver-vs-hfss-crossvalidation-plan.html](../docs/solver-vs-hfss-crossvalidation-plan.html)
