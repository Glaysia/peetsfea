# generate_type2_step.py

## Source
- Path: `entry/generate_type2_step.py`
- Code note path: `sdd/code/entry/generate_type2_step.py.md`
- Related plan: [[sdd/plans/0.2.22-type2-toml-unification]]
- Related umbrella plan: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- Related architecture: [[sdd/architecture/type2-step-to-em-validate-pipeline]]
- Related test: [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 역할
- `examples/type2.toml`을 단일 type2 authoring input으로 읽는다.
- `[[non_model_objects]]`와 `[[modeled_objects]]`를 object-level STEP artifact로 export한다.
- object-level STEP 결과를 metadata ledger(`type2_step_ledger.json`)로 기록한다.
- direct single-coil CLI consumers can export the modeled `tx_single_coil` object from the same type2 TOML without using a standalone TOML input.

## 입력 / 출력
- 입력: `examples/type2.toml`
- 출력 디렉터리 기본값: `run/step/type2`
- 출력 artifact:
  - `run/step/type2/objects/<object_id>.step`
  - `run/step/type2/metadata/<object_id>.metadata.json` (modeled objects only)
  - `run/step/type2/type2_step_ledger.json`
- CLI entry: `.venv/bin/python entry/generate_type2_step.py`

## Canonical state
- module-level mutable state는 없다.
- canonical 입력은 `type2.toml`의 object registry다.
- canonical export ledger는 `type2_step_ledger.json`이며 AEDT geometry reverse-calculation 없이 생성 시점 metadata를 유지한다.
- modeled object metadata keeps `source_toml_path` as the type2 TOML path even though the internal `tx_rect_void` parser is reused.

## Invariants / fail-fast
- `design.units`는 `mm`여야 한다.
- `non_model_objects`, `modeled_objects`는 각각 non-empty array of tables여야 한다.
- object id는 non-model/modeled 합쳐 중복되면 안 된다.
- non-model object는 `primitive=box`, `present=true`, `non_model=true`, valid plane, positive `size_xyz`를 만족해야 한다.
- modeled object role은 현재 `tx_single_coil`만 허용한다.
- prototype 단계에서 `modeled_objects`는 정확히 1개여야 한다.
- prototype modeled object는 `object_id = tx_rect_void_coil`, `material = composite`를 강제한다.
- modeled object는 `model_state=true`여야 한다.
- modeled object range/terminal fields 누락 또는 타입 위반은 즉시 실패한다.
- modeled object uses `outer_y_mm`; ratio-based outer-y input is no longer accepted.
- `tx_rect_void` export path에서 invalid terminal path, void overlap, unsupported multilayer, range invalid는 즉시 실패한다.
- modeled export must record expected exported body names/count for import smoke validation.
- `build123d.export_step()`가 `False`를 반환하면 즉시 예외로 중단한다.

## 직접 의존
- Python 표준 라이브러리: `argparse`, `json`, `pathlib`, `tempfile`, `tomllib`
- 외부 라이브러리: `build123d`
- core geometry reuse: [[sdd/code/src/peetsfea/tx_rect_void.py]]

## 이 파일을 쓰는 곳
- type2 object-level STEP authoring CLI.
- worker2 import/viewer path가 소비할 type2 artifact producer.

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- modeled object schema field를 바꾸면 `type2.toml`과 테스트 fixture를 함께 갱신한다.
- ledger 필드 shape를 바꾸면 downstream import smoke contract를 함께 갱신한다.
- 새 modeled role을 추가할 때는 명시적으로 parser/dispatcher를 확장하고 unsupported role fail-fast를 유지한다.
