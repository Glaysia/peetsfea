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
radiation_margin_mm = 3500.0
setup_frequency_hz = 6.78e6
sweep_start_hz = 1.0e6
sweep_stop_hz = 45.0e6
validation_gate = "hard_fail"
max_delta_s = 0.001
maximum_passes = 35
minimum_passes = 9
minimum_converged_passes = 13
percent_refinement = 65
basis_order = 1
port_accuracy = 2

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

### 리팩토링된 모듈 경로
- Geometry 엔트리포인트: `peetsfea.backend.pyaedt.geometry.build.build_square_spiral_from_manifest`
- Resolver 엔트리포인트: `peetsfea.spec.resolver.resolve_selection`, `peetsfea.spec.resolver.resolve_selected_parameters`
- Candidate builder 공개 경로: `peetsfea.spec.resolver.sampling.build_candidates`

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

### TxDD 우측-only 단계 계약
- 이번 단계는 `tx_dd` 우측(right) endpoint 규칙만 적용한다.
- `geometry_metadata.group_endpoints[*]`에 `start_label`, `end_label`이 기록된다.
- 규칙:
  - `tx_dd selected_count=2`(1층): 우측 코일 `C -> d`, 전류 방향 `ccw`
  - `tx_dd selected_count=4`(2층): 우측 하층/상층 순서로 `c -> A`, `A -> d`, 둘 다 `ccw`
- 하층/상층 판정은 endpoint `z_center=(start_z+end_z)/2` 오름차순으로 결정한다.
- 이번 단계 제외 범위: `tx_dd` 좌측, `tx_vertical`, `rx_dd`, 리드/유나이트 확장

### RxDD endpoint 계약 (TX 스타일 매핑)
- 기준 뷰는 `+X` 정면이며, 이 기준에서 `오른쪽=+Y`, `위=+Z`로 본다.
- `rx_dd`는 단층만 지원하며 `selected_count=2`가 아니면 실패한다.
- `rx_dd`는 우측 기준 경로 생성 계약을 사용한다:
  - right(`off_y > 0`): `A -> d`, `cw`
  - left(`off_y < 0`): right 경로를 월드 Y 중심축(`y = rx_center_y + dy`)으로 반사한 대칭, `B -> c`, `ccw`
- 라벨은 후처리 덮어쓰기가 아니라 코일 생성 시점 계약으로 기록한다.

- 실행:
```bash
python run.py
```
- VS Code launch(`Run run.py from run/`)는 pre-launch task로 `run/aedt/`를 먼저 비운 뒤 실행한다.
- 기본 TOML 예시: `examples/type1.toml` (grouped 구조)
  - `coil_shape.tx_dd|tx_vertical|rx_dd.outer_x/outer_y`: 그룹별 코일 외곽 치수
  - `tx_dd_pair_spacing_mm`, `rx_dd_pair_spacing_mm`는 ratio에서 파생되는 내부 추적값
  - 파생 변수 더미 표기: `range = [false, -1, -1, -1]`
    - 더미 표기를 사용하는 경로는 샘플링하지 않고 코드에서 파생해야 한다.
    - 현재 매핑: `coil_shape.tx_vertical.outer_x -> coil_shape.tx_dd.outer_x`
  - PCB Z 파생 규칙:
    - `pcbs[].z_mode`는 `absolute | relative_to_pcb`를 사용한다.
    - `relative_to_pcb`일 때 최종 z는 `<base>.z + sample(z_delta_path)`로 파생한다.
    - 기본 예시: `tx_main_1`은 `z_relative_base_id="tx_main_0"`, `z_delta_path="pcb_spacing.tx_main_1_z_from_tx_main_0_mm"`.
  - 0.2.6 고정 토폴로지 규칙:
    - 코일 개수(`selected_coil_groups`)가 주도하고 PCB `present/mounts`는 정규화된다.
    - `tx_vertical`은 전용 보드 `tx_vertical_0`에만 매핑된다.
    - `tx_opt_*/rx_opt_*`는 호환 필드로 남기되 기본 경로에서 강제로 비활성(`present=false`, `mounts=[]`) 처리된다.
    - 입력이 고정 규약과 다르면 `UserWarning`을 발생시키고 자동 보정한다.
- 그룹별 자유변수는 `[coil_groups_params.<kind>]` 아래에서 독립 정의한다.
  - 고정 그룹 키: `tx_dd`, `tx_vertical`, `rx_dd`
  - 각 그룹은 `turn_count_max`, `band_ratio`, `metal_ratio`를 각각 별도 range로 가진다.
  - `trace/gap`는 입력값이 아니라 파생값이다.
    - `effective_outer_y = min(<group>.outer_y, tx_region_vertical_z_mm)` for `tx_vertical`, else `<group>.outer_y`
    - `base_outer = min(<group>.outer_x, effective_outer_y)`
    - `band_mm = band_ratio * base_outer`
    - `pitch_mm = band_mm / turn_count_max`
    - `trace = pitch_mm * metal_ratio`
    - `gap = pitch_mm * (1 - metal_ratio)`
  - 동일 TOML+seed면 그룹별 선택값(`selected_group_geometry`)도 결정론적으로 동일하다.
- 제약식은 TOML의 SSOT 섹션인 `[constraints]` + `[[constraints.rules]]`로 선언한다.
  - `kind = "comparison"`: `lhs.path`와 `rhs.path|rhs.value|rhs.func`를 `op`로 비교
  - `kind = "range"`: `target.path`를 `min/max`로 범위 제한
  - `kind = "aggregate"`: 현재는 `agg = "sum_group_selected_count"` 지원
  - `rhs.func`는 `add(...)`, `mul(...)`, `min(...)`, `max(...)`, `sub(...)`, `active_group(kind)`, `feasible_turns(...)`, `feasible_turns_max(...)`, `max_mount_selector_index(kind)`, `max_supported_mount_index(kind)`를 지원
  - `tx_vertical`의 자유도는 `tx_vertical_center_gap_mm`이며, resolver는 `tx_vertical_span_mm = center_gap * max(0, selected_count - 1)`로 파생한다.
  - `tx_vertical` 배치 규칙: 짝수 개수는 `±d/2, ±3d/2 ...`(`d = tx_vertical_center_gap_mm`), 홀수 개수는 가운데 코일 외곽이 X축에 접하고 나머지는 X축 대칭으로 배치한다.
  - `tx_vertical_center_gap_range` 규칙으로 `tx_vertical_center_gap_mm >= 1.62`를 강제한다.
  - `constraints.rules`는 필수이며 누락/빈 값이면 실행 전 실패한다.
  - 목적은 GA/딥러닝 샘플러가 동일 TOML 제약을 사전 필터에 재사용하는 것이다.
- 하드코딩 설계값은 TOML로 승격되어 resolver/geometry 입력으로 직접 사용된다.
  - `[coil_material]`: `via_diameter_mm`, `pcb_thickness_mm`, `cu_thickness_mm`, `fr4_er`
  - `[scene_anchor]`: `shelf_height_mm`, `shelf_min_size_x_mm`, `rx_region_bottom_from_tv_mm`
  - `[coil_placement]`: `tx_dd_top_clearance_mm`, `rx_face_clearance_mm`, `dd_mirror_plane`, `rx_plane`, `tx_vertical_plane`
  - `[simulation]`: `radiation_margin_mm`, `setup_frequency_hz`, `sweep_start_hz`, `sweep_stop_hz`, `validation_gate`, `max_delta_s`, `maximum_passes`, `minimum_passes`, `minimum_converged_passes`, `percent_refinement`, `basis_order`, `port_accuracy`
    - setup의 나머지 옵션은 코드 하드코딩을 유지하고, 위 핵심 adaptive 숫자만 TOML에서 조정한다.
    - radiation region은 model bbox 기준 전방향 `Absolute Offset`(기본 `±3500mm`)으로 생성한다.
  - 현재는 TOML 계약 고정을 위해 대부분 `count=1`(또는 단일 문자열)로 선언한다.

동작 요약:
1) TOML 원본 바이트 SHA-256(`toml_hash`) 계산
2) `git rev-parse HEAD`로 40자 커밋 해시 확인
3) `git rev-parse HEAD`로 커밋 해시를 기록 (dirty 상태도 허용)
4) seed/attempt 오프셋 방식으로 파라미터별 단일 설계 원소 선택
  - 동일 attempt 내에서는 같은 TOML path를 여러 내부변수가 참조해도 단일 샘플을 공유한다.
  - 제약 실패 시 deterministic retry(`attempt += 1`)를 수행한다.
5) `toml_hash` 앞 8글자로 `toml_space_hash` 생성
6) `toml_hash + commit + selected_parameters + selected_group_geometry + selected_coil_groups + selected_pcbs`의 SHA-256 앞 8글자로 `design_unique_hash` 생성
7) `design_id = <design_unique_hash>_<toml_space_hash>_<seed>_<attempt>` 조합
8) `<ansys_run_dir>/<design_id>.aedt`, `geometry_metadata_<design_id>.json`, `manifest_<design_id>.json` 저장
  - `manifest/metadata.repro_mode`: `sampled_toml | frozen_toml | manifest_json`

## Internal Architecture (0.2.6)
### Geometry Build Pipeline
- 엔트리포인트 `build_square_spiral_from_manifest`는 다음 오케스트레이션 단계로 분리되어 동작한다.
  - `_prepare_runtime`: manifest/prelude 검증과 런타임 컨텍스트 구성
  - `_build_scene`: scene non-model 오브젝트 생성 + region/center 계산
  - `_build_all_coils`: 그룹별 코일 생성기(`tx_dd`, `tx_vertical`, `rx_dd`) 호출
  - `_finalize_geometry`: 브리지/스텁/FR4/subtract/final save 수행
  - `_build_and_save_metadata`: 디버그/EM pipeline/metadata JSON 저장
- 내부 상태는 `GeometryRuntimeContext`, `GeometryBuildState`, `FinalizeInputs` 타입으로 관리한다.

### Finalize Pipeline
- `finalize_solids_and_substrates`는 공개 함수(얇은 진입점)이며 내부 구현에서 단계적으로 브리지/유나이트/FR4/subtract를 수행한다.
- 반복되는 `modeler.unite` 호출은 `safe_unite(modeler, targets, fallback_name, error_context)`를 사용해 통일한다.

### Resolver Dispatch
- 제약식 경로 해석은 prefix 기반 dispatch(`selected_group_geometry`, `selected_coil_groups`, `selected_pcbs`, `selected_mounts`, scalar)로 분리했다.
- 함수식 해석(`rhs.func`)은 `FUNC_DISPATCH` 형태의 딕셔너리 기반 핸들러로 평가한다.

### Local Quality Gates
- 기본 검증 명령:
```bash
cd run
../.venv/bin/pytest -q ../tests
../.venv/bin/pyright ../src ../tests ../run.py
../.venv/bin/mypy ../src ../tests ../run.py
```

## 기여
아직 초기 단계다. 아이디어/요구사항/스펙 제안은 언제든 환영한다.
