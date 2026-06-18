# pfsolver — open-source full-wave FEM solver (HFSS replacement)

HFSS를 대체해 0.3.7 STEP 번들에서 terminal-network Z(f)를 산출한다.

## 아키텍처 (pyaedt → ansysedt 구도)
- **pfsolver = 독립 Python API 서브프로젝트** (`solver/pfsolver`, pyright strict + pydantic). **도커 밖**.
  번들 ingest → gmsh(Python) 메시 → Palace config emit → `~/.local/bin/palace` 엔진 래퍼 호출 → CSV→Z → manifest.
- peetsfea-facing CLI는 없다. peetsfea는 나중에 `pfsolver` Python API를 import/call한다.
- 컨테이너 런타임은 Palace 래퍼가 숨긴다. 현재 로컬 dev 기본은 Docker 이미지
  `peetsfea-palace:0.16.1pfterm01` (`PFSOLVER_CONTAINER_RUNTIME=docker`,
  `PFSOLVER_PALACE_IMAGE=peetsfea-palace:0.16.1pfterm01`). stock `palace:0.16.1`은 no-ferrite
  회귀 진단용이다.
- **C++은 Palace 엔진 안에만** (주파수 종속 복소 μ 패치는 Palace fork). 오케스트레이터엔 C++ 없음.
- `pfsolver`와 Palace의 안정 인터페이스 = **Palace wrapper CLI(JSON config / CSV)**. Palace엔 stable 공개 libpalace 없음.

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
    Dockerfile.base            # forked Palace CUDA 엔진 이미지(포크 단계)
    build.sh                   # docker build -> peetsfea-palace:0.16.1pfterm01(포크 단계)
    shell.sh                   # GPU 붙은 dev 컨테이너 셸 (포크 빌드/palace 실행)
  pfsolver/                    # 독립 Python API 서브프로젝트(별도 서브모듈 대상)
  docs/implementation-plan-phase-A-C.md
```

## Palace 엔진 래퍼
```bash
~/.local/bin/palace --version
```
CUDA mandatory: 래퍼의 이미지는 CUDA-only 빌드다. 오케스트레이터가 invoke 전 GPU 게이트(no CPU fallback).

## 상세
- 목표/Acceptance: [../GOAL.md](../GOAL.md)
- Phase A–C 계획: [docs/implementation-plan-phase-A-C.md](docs/implementation-plan-phase-A-C.md)
- 교차검증: [../docs/solver-vs-hfss-crossvalidation-plan.html](../docs/solver-vs-hfss-crossvalidation-plan.html)
