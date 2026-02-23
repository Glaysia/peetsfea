# peetsfea

Pyaedt 기반으로 TOML 명세를 해석해 변압기 코일/자기결합 무선전력전송(IPT) 기기를 결정론적으로 설계하고, 대량 데이터셋을 생성하는 파이썬 라이브러리.

문서화를 충분히 해두어 LLM 기반 설계 워크플로우에 유용하게 쓰는 것을 목표로 한다.
TOML은 기본적으로 여러 파라미터 범위 안의 설계 셋을 정의하며, TOML은 단 하나의 Pyaedt 파이썬 코드와 일대일 대응된다.
이 파이썬 코드는 실행 시 전달되는 숫자 시드를 내부 랜덤 시드로 사용하고, (TOML + 시드 숫자)가 최종 파라미터에 일대일 대응된다.

## 목표
- 코드보다 명세 중심: 설계는 TOML로, 실행/스케줄링은 파이썬 코드로 관리한다.
- 결정론: 동일 명세 + 동일 버전 + 동일 시드 = 동일 결과.
- 확장성: 새로운 기기/코일 타입을 스펙 추가만으로 확장.
- 데이터셋 생산: 다양한 파라미터 조합을 체계적으로 생성.

## 핵심 개념
1) **Spec (TOML)**: 기기 구조와 물성, 해석 조건을 기술한다.  
2) **Compiler/Builder**: 명세를 해석해 결정론적 설계 그래프로 변환한다.  
3) **Backend (Pyaedt)**: 실제 모델링/시뮬레이션을 수행한다.  
4) **Dataset Generator**: Sweep/DOE를 통해 대량 데이터셋을 생성한다.

실행 타깃과 스케줄링은 파이썬 코드에서 관리하며, TOML은 설계에 대한 SSOT로 유지한다.

## 범위
- 변압기/코일 설계(공심/코어, 다양한 권선 형태).
- 자기결합 IPT 기반 무선전력전송 구조 설계.
- 파라미터 스윕/샘플링을 통한 데이터셋 생성.
- 설계 생성 전 스펙을 먼저 읽고, 가능한 것/불가능한 것을 판별해 피드백한다.
- AEDT는 GUI를 끄고 headless로 실행하는 것을 전제로 한다.

## 비범위(현재)
- UI 기반 설계 도구.
- 범용 전자기 시뮬레이터 대체.
- “새로운 언어” 수준의 문법 설계(표준 TOML 사용).

## 테스트 환경
- Python 3.12
- AEDT 25 R2: Windows 10/11, Kubuntu 25
- AEDT 25 R2: Rocky 8.8

신버전이 나오면 계속 버전을 올릴 예정이라 하위 호환성에 불편이 있을 수 있어 미안하다. 내 성향이 그렇다.

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

## run.py MVP (함수 호출 기반)
현재 MVP는 `run.py`에서 CLI 인자 없이 `RunConfig`를 사용해:
1) manifest JSON 생성
2) HFSS 3D Modeler로 사각 PCB 스파이럴 코일 형상 생성
3) `.aedt + geometry metadata JSON` 저장
4) 출력 산출물 경로는 하드코딩된 `run/aedt/`를 사용

### Geometry generation contract (centerline-first)
- 사각 스파이럴은 `copper outer edge/corner` 기준으로 centerline을 먼저 절대좌표로 생성한다.
- 모든 세그먼트는 축 정렬(axis-aligned)이며, turn pitch는 `trace + gap`으로 고정된다.
- 코너 처리는 방향별 분기 대신 벡터 회전 규칙(`cross_z`)으로 분류한다.
- `geometry_metadata_<design_id>.json`에는 다음 디버그 정보가 포함된다.
  - `anchor_mode = "copper_outer_edge_corner"`
  - `debug.centerline_vertices`
  - `debug.corner_debug` (corner type, incoming/outgoing dir, offset)
  - `debug.axis_checks`, `debug.pitch_checks`
  - `debug.cad_probe` (CAD bbox/edge 샘플 좌표)
  - `debug.constraints_ok`
  - `debug.in_region_ok`, `debug.violations` (영역 포함성 검사)

- 실행:
```bash
python run.py
```
- VS Code launch(`Run run.py from run/`)는 pre-launch task로 `run/aedt/`를 먼저 비운 뒤 실행한다.
- 기본 TOML 예시: `examples/type1.toml` (grouped 구조)
- 프로필은 `[[trace_gap_profile.profiles]]` 배열로 정의한다.
  - 각 프로필은 `id`, `trace`, `gap`을 가진다.
  - `seed` 기준 선택 규칙: `(seed + 300) % len(profiles)` (결정론).
  - 목적은 최적화가 아니라 데이터셋 다양성 확보이며, 운영 권장 개수는 5개다.
- 제약식은 TOML의 SSOT 섹션인 `[constraints]` + `[[constraints.rules]]`로 선언한다.
  - `kind = "comparison"`: `lhs.path`와 `rhs.path|rhs.value|rhs.func`를 `op`로 비교
  - `kind = "range"`: `target.path`를 `min/max`로 범위 제한
  - `kind = "aggregate"`: 현재는 `agg = "sum_group_selected_count"` 지원
  - `rhs.func`는 `min(path_a,path_b)`, `sub(path_a,path_b,path_c)`만 지원
  - `constraints.rules`는 필수이며 누락/빈 값이면 실행 전 실패한다.
  - 목적은 GA/딥러닝 샘플러가 동일 TOML 제약을 사전 필터에 재사용하는 것이다.
- 하드코딩 설계값은 TOML로 승격 중이며, 1차로 다음 섹션이 추가됐다.
- 하드코딩 설계값은 TOML로 승격되어 resolver/geometry 입력으로 직접 사용된다.
  - `[coil_material]`: `via_diameter_mm`, `pcb_thickness_mm`, `cu_thickness_mm`, `fr4_er`
  - `[scene_anchor]`: `shelf_height_mm`, `shelf_min_size_x_mm`, `rx_region_bottom_from_tv_mm`
  - `[coil_placement]`: `tx_dd_top_clearance_mm`, `rx_face_clearance_mm`, `dd_mirror_plane`, `rx_plane`
  - 현재는 TOML 계약 고정을 위해 대부분 `count=1`(또는 단일 문자열)로 선언한다.

동작 요약:
1) TOML 원본 바이트 SHA-256(`toml_hash`) 계산
2) `git rev-parse HEAD`로 40자 커밋 해시 확인
3) `git rev-parse HEAD`로 커밋 해시를 기록 (dirty 상태도 허용)
4) seed 오프셋 방식으로 파라미터별 단일 설계 원소 선택
5) `toml_hash` 앞 8글자로 `toml_space_hash` 생성
6) `toml_hash + commit + seed + selected_parameters`의 SHA-256 앞 8글자로 `design_unique_hash` 생성
7) `design_id = <design_unique_hash>_<toml_space_hash>_<seed>` 조합
8) `<ansys_run_dir>/<design_id>.aedt`, `geometry_metadata_<design_id>.json`, `manifest_<design_id>.json` 저장

## 기여
아직 초기 단계다. 아이디어/요구사항/스펙 제안은 언제든 환영한다.
