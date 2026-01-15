# PeetsFea

Pyaedt 기반으로 TOML 명세를 해석해 변압기 코일/자기결합 무선전력전송(IPT) 기기를 결정론적으로 설계하고, 대량 데이터셋을 생성하는 파이썬 라이브러리.

## 목표
- 코드보다 명세 중심: 사용자는 TOML만 작성한다.
- 결정론: 동일 명세 + 동일 버전 + 동일 시드 = 동일 결과.
- 확장성: 새로운 기기/코일 타입을 스펙 추가만으로 확장.
- 데이터셋 생산: 다양한 파라미터 조합을 체계적으로 생성.

## 핵심 개념
1) **Spec (TOML)**: 기기 구조와 물성, 해석 조건을 기술한다.  
2) **Compiler/Builder**: 명세를 해석해 결정론적 설계 그래프로 변환한다.  
3) **Backend (Pyaedt)**: 실제 모델링/시뮬레이션을 수행한다.  
4) **Dataset Generator**: Sweep/DOE를 통해 대량 데이터셋을 생성한다.

## 범위
- 변압기/코일 설계(공심/코어, 다양한 권선 형태).
- 자기결합 IPT 기반 무선전력전송 구조 설계.
- 파라미터 스윕/샘플링을 통한 데이터셋 생성.

## 비범위(현재)
- UI 기반 설계 도구.
- 범용 전자기 시뮬레이터 대체.
- “새로운 언어” 수준의 문법 설계(표준 TOML 사용).

## TOML 명세 예시
아래는 방향성을 보여주는 최소 예시다. 실제 스키마는 프로젝트 진행과 함께 확정된다.

```toml
[spec]
version = "0.1"

[project]
name = "ipt_demo"
units = "mm"
backend = "pyaedt"

[geometry]
type = "ipt"
stack = "planar"

[coupling]
gap = 3.0

[coil.primary]
turns = 12
shape = "spiral"
inner_diameter = 20.0
pitch = 1.3
wire = { diameter = 1.0, insulation = 0.1 }

[coil.secondary]
turns = 8
shape = "spiral"
inner_diameter = 18.0
pitch = 1.3
wire = { diameter = 1.0, insulation = 0.1 }

[simulation]
solution = "frequency"
frequency = 100e3

[dataset]
enabled = true
method = "lhs"
samples = 200
seed = 42

[[dataset.parameters]]
path = "coupling.gap"
range = [1.0, 6.0]
samples = 20

[[dataset.parameters]]
path = "coil.primary.turns"
values = [8, 10, 12, 14]
```

## 출력(예정)
- Pyaedt 프로젝트 파일과 해석 결과.
- 설계 파라미터 및 결과값 CSV/Parquet.
- 실행 로그 및 재현 정보(버전/시드).

## 개발 로드맵(초안)
1) TOML 스키마 정의 및 검증기 구현.
2) 스펙 → 설계 그래프 변환기 구현.
3) Pyaedt 백엔드 구현(기본 IPT/변압기 템플릿).
4) 데이터셋 생성기(스윕/샘플링/태그) 구현.

## 기여
아직 초기 단계다. 아이디어/요구사항/스펙 제안은 언제든 환영한다.

