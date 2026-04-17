---
title: type2 재사용 자산 분석
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 09:09
tags:
  - type2
---

# type2 재사용 자산 분석

## 목적
- 이 문서는 `type2`를 구현하기 전에 현재 `type1` 코드베이스에서 무엇을 그대로 가져가고, 무엇을 분리한 뒤 재사용해야 하는지 분류하는 내부 설계 메모다.
- 기준 릴리즈는 현재 문서 기준과 같은 `0.2.22`이다.
- 판단 기준은 "새 형상 타입이 들어와도 계약이 유지되는가"와 "이름/배치/토폴로지가 `type1`에 박혀 있는가"다.

## 재사용 등급
- `그대로 재사용`: `type1`이라는 형상 이름 없이도 바로 쓸 수 있는 공통 인프라/유틸리티.
- `조건부 재사용`: 핵심 로직은 공통이지만 계약 주입점이나 타입 분리가 먼저 필요한 것.
- `type1 결합 높음`: 현재 이름, 배치 규칙, 고정 토폴로지, 컨텍스트 문자열이 `type1`에 직접 묶여 있는 것.

## sampling/selection

```python
result = resolve_selection_result(spec=spec, seed=seed, attempt=attempt)
selected = result.selected_parameters
groups = result.selected_coil_groups
geometry = result.selected_group_geometry
pcbs = result.selected_pcbs
```

| 대상 | 현재 역할 | 재사용 등급 | 재사용 이유 | type2에서 필요한 조치 |
| --- | --- | --- | --- | --- |
| `src/peetsfea/spec/resolver/api.py::resolve_selection_result()` | 샘플링 레지스트리, scalar selection, coil group selection, geometry selection, pcb resolution, constraint validation을 하나의 결과로 묶는다. | 조건부 재사용 | selection 파이프라인 구조 자체는 공통이지만 `type1` 전용 scalar path와 group kind 집합에 의존한다. | `type2`용 selected contract를 주입할 수 있게 scalar/group/pcb resolver 경계를 분리한다. |
| `src/peetsfea/spec/resolver/sampling.py` | canonical owner registry, preflight, deterministic candidate selection을 담당한다. | 그대로 재사용 | owner-path 기반 sampling과 retry/attempt 모델은 형상 타입과 독립적이다. | 새 sampled path를 registry에 추가하되 기존 canonical ownership 규칙을 유지한다. |
| `src/peetsfea/pipeline/uniform_seedset.py` | feasible seed를 모으고 sampled-coordinate 공간에서 eager uniform selection을 수행한다. | 그대로 재사용 | 입력이 `spec_path`와 sampling ledger뿐이라 geometry kind와 분리되어 있다. | `dataset_owner_paths()`가 `type2` owner set을 읽을 수 있게만 맞추면 된다. |
| `src/peetsfea/spec/resolver/group_geometry.py` | `turn_count`, `band_ratio`, `metal_ratio`에서 `trace`/`gap`을 파생한다. | 조건부 재사용 | 파생 공식은 공통 후보가 될 수 있지만 현재 `GROUP_KIND_ORDER`와 `tx_vertical` 특례를 안고 있다. | kind별 외곽 치수 조회를 인터페이스로 빼고 `type2` geometry family를 추가한다. |
| `src/peetsfea/spec/resolver/constants.py::{GROUP_KIND_ORDER,FIXED_PCB_RULES}` | group 순서, scalar path, fixed PCB topology를 SSOT처럼 고정한다. | type1 결합 높음 | `tx_dd`, `tx_vertical`, `rx_dd`와 `tx_main_0` 같은 이름이 직접 박혀 있다. | `type1`용 policy 모듈로 내리고, 새 타입은 별도 topology/policy를 제공하게 한다. |

## run/pipeline

```python
selected_points = generate_eager_uniform_feasible_seed_points(...)
entry = generate_sample_artifact_for_seed(...)
result = run(config)
resolved_toml_path = write_resolved_toml(...)
write_sample_manifest(entries, manifest_path)
```

| 대상 | 현재 역할 | 재사용 등급 | 재사용 이유 | type2에서 필요한 조치 |
| --- | --- | --- | --- | --- |
| `src/peetsfea/pipeline/run_design.py::run()` | spec 검증, deterministic selection, manifest 생성, `repro_snapshot`/`dataset_snapshot`/`source_toml_bytes` 구성을 담당한다. | 그대로 재사용 | `RunResult`와 manifest 골격은 형상 생성 전 단계의 공통 계약이다. | `SUPPORTED_SPEC_VERSION`과 spec parser가 `type2` 경로를 받아들일 수 있게만 확장한다. |
| `src/peetsfea/pipeline/run_batch.py` | sample artifact 생성, resolved TOML 작성, frozen TOML gate, build 재진입, 실패 정리를 담당한다. | 그대로 재사용 | run/build를 분리한 2단 파이프라인 자체는 `type2`에도 그대로 필요하다. | geometry builder 진입점만 타입별 디스패치 가능하게 바꾼다. |
| `src/peetsfea/pipeline/selection_snapshots.py` | `repro.toml`/`dataset.toml` 논리 산출물과 frozen range 변환을 정의한다. | 그대로 재사용 | sampled owner ledger와 replay snapshot의 역할 분리는 형상 타입과 독립적이다. | `type2` sampled owner set이 canonical registry를 따르도록 유지한다. |
| `entry/sample.py`, `entry/build.py` | 현재 표준 배치 샘플/빌드 진입점을 제공한다. | 그대로 재사용 | entry 스크립트는 `run()`과 `run_batch` orchestration 위에 얹힌 thin wrapper다. | 기본 TOML 경로와 geometry dispatch만 `type2` 선택을 허용하면 된다. |
| `entry/sample_build.py` | 미리 생성된 batch manifest를 GUI-visible runtime으로 순차 replay하는 디버그 플로우를 제공한다. | 조건부 재사용 | 디버그 워크플로 자체는 공통이지만 현재 기본 batch series와 source TOML이 `type1` 전용이다. | `type2` debug profile과 source TOML 선택 방식을 분리한다. |

## geometry primitive

```python
points = _build_rect_spiral_centerline_absolute(...)
points = _translate_points(points, dx=dx, dy=dy, dz=dz)
yz_points = _map_xy_points_to_yz(points, x_const=x0, y_center=y0, z_center=z0)
probe = _probe_cad_object(obj)
name = safe_unite(modeler=modeler, targets=targets, error_context=context)
```

| 대상 | 현재 역할 | 재사용 등급 | 재사용 이유 | type2에서 필요한 조치 |
| --- | --- | --- | --- | --- |
| `src/peetsfea/backend/pyaedt/geometry/spiral_points.py` | centerline 생성, 평면 변환, mirror, translate 같은 점 기반 기하 유틸을 제공한다. | 그대로 재사용 | point transform 계열은 `type1` 고유 이름 없이 가장 재사용성이 높다. | 새 형상 primitive가 필요하면 같은 레이어에 추가하고 기존 함수는 그대로 유지한다. |
| `src/peetsfea/placement_math.py::tx_vertical_center_x_from_tx_dd_min()` | ratio 기반 위치 계산을 수행한다. | 조건부 재사용 | 수학 함수 자체는 단순하지만 현재 의미가 `tx_vertical` 배치에 직접 묶여 있다. | 이름과 입력 의미를 일반화한 placement utility로 승격한다. |
| `src/peetsfea/backend/pyaedt/geometry/cad_probe.py` | live CAD object의 bbox/edge sample을 추출한다. | 그대로 재사용 | 검증/메타데이터용 probe는 coil 종류와 무관하다. | 새 객체 이름 규칙이 들어와도 실제 CAD object 이름을 그대로 읽는 fail-fast 계약으로 유지한다. |
| `src/peetsfea/backend/pyaedt/geometry/solid_ops.py` | Pyaedt `unite()` 차이를 흡수하고 안전한 unite 이름을 정규화한다. | 그대로 재사용 | backend API 흡수층이라 형상 타입과 무관하다. | 새 builder도 union이 필요하면 그대로 호출한다. |
| `src/peetsfea/backend/pyaedt/geometry/design_vars.py::_assign_design_variables()` | sampling owner를 AEDT design variable로 주입한다. | 조건부 재사용 | design variable 주입 패턴은 공통이지만 owner path -> selected value 매핑이 `type1` path와 group index에 의존한다. | owner-path 해석기를 타입별 adapter로 분리한다. |

## geometry builder/finalize + EM

```python
ctx = _prepare_runtime(manifest)
_build_scene(ctx, state, modeler)
finalize_inputs = _build_all_coils(ctx, state, modeler)
_finalize_geometry(ctx, state, finalize_inputs, modeler, hfss)
run_em_pipeline(hfss, modeler, em_input, em_policy, outputs)
```

| 대상 | 현재 역할 | 재사용 등급 | 재사용 이유 | type2에서 필요한 조치 |
| --- | --- | --- | --- | --- |
| `src/peetsfea/backend/pyaedt/geometry/build.py` | runtime 준비, scene/coils/finalize/ferrite orchestration, metadata 저장, HFSS session 종료를 묶는다. | type1 결합 높음 | 필수 kind를 `tx_dd`, `tx_vertical`, `rx_dd`로 가정하고 전체 호출 순서가 `type1` scene 계약에 맞춰져 있다. | 공통 build shell과 타입별 build plan을 분리한다. |
| `src/peetsfea/backend/pyaedt/geometry/group_builder_{tx_dd,tx_vertical,rx_dd}.py` | 각 coil group의 개별 형상과 endpoint/polarity를 생성한다. | type1 결합 높음 | 이름, plane, winding, board mount 규칙이 `type1` group semantics에 깊게 묶여 있다. | `type2`는 별도 builder를 만들고, 공통 point/validation 유틸만 공유한다. |
| `src/peetsfea/backend/pyaedt/geometry/scene_objects.py` | TV, wall, floor, tx/rx region, ferrite object의 scene 및 ferrite 배치 계약을 구현한다. | type1 결합 높음 | scene/ferrite 배치 계약이 TV/wall IPT 배치에 직접 의존한다. | scene contract를 `type1` 전용과 공통 scene helper로 분해한다. |
| `src/peetsfea/backend/pyaedt/geometry/build_rx_dd.py::{finalize_solids_and_substrates,build_em_artifacts}` | bridge/stub/fr4 finalize와 EM 입력용 ready object/context를 만든다. | 조건부 재사용 | finalize 패턴과 EM 입력 묶음은 재사용 가능하지만 object naming과 terminal contract가 `type1` coil 구성에 묶여 있다. | EM-ready object assembler를 공통층으로 빼고 type-specific endpoint naming은 adapter로 둔다. |
| `src/peetsfea/backend/pyaedt/em_pipeline/*` | boundary, ports, sources, analysis, report template, validation을 수행한다. | 그대로 재사용 | HFSS EM pipeline은 `EmPipelineInput`과 `outputs` 계약만 맞으면 geometry 종류와 분리된다. | `em_context["source"]`의 현재 `"type1_geometry"` 고정 문자열은 타입별 상수 또는 manifest 기반 값으로 치환한다. |

## type2 구현 전에 먼저 분리할 seam
- `selection contract`: `resolve_selection_result()`의 공통 뼈대와 `type1` path/group/topology policy를 분리한다.
- `shape/placement utility`: `spiral_points.py`, `placement_math.py`, 일부 `placement_rules.py`를 type-specific naming 없이 호출 가능한 계층으로 정리한다.
- `type-specific builder orchestration`: `geometry/build.py`의 공통 HFSS lifecycle과 `type1` builder dispatch를 분리해 `type2`가 같은 shell 위에 올라오게 만든다.
