# Type2 TX Rect/Void Single-Coil STEP Prototype

## Goal
- `tx_rect_void`를 standalone 실험이 아니라 type2의 첫 modeled single-coil prototype으로 승격한다.
- TOML을 SSOT로 삼아 외곽 사각형, movable void keepout, side-local fill, 1-3 stacked PCB layer를 결정론적으로 실현한다.
- 출력은 `single modeled TX coil STEP + metadata`로 고정하고, 이 metadata를 future type2 object registry의 첫 concrete modeled-object contract로 삼는다.

## Scope
- 포함:
  - [[sdd/code/src/peetsfea/tx_rect_void.py]]
  - [[sdd/code/entry/export_tx_rect_void_step.py]]
  - [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]
  - `examples/tx_rect_void/tx_rect_void_coil.toml`
  - [[docs/tx-rect-void-step]]
- 제외:
  - AEDT import, HFSS launch, EM ports, source assignment, solve
  - type2 runtime manifest/build dispatch 연결
  - generic multi-coil family 설계

## Decisions
- 이 단계의 제품 의미는 type2 modeled object의 첫 concrete milestone이다.
- STEP 생성은 `build123d`를 사용하고, 출력 기본 위치는 `run/step/`다.
- prototype 산출물은 object-registry 관점의 modeled object metadata를 남긴다. metadata JSON은 기존 `realized`/`boxes`를 유지하면서 single-entry `modeled_objects` proto-contract를 추가한다.
- `modeled_objects[0]`의 최소 필드는 `object_id`, `role`, `material`, `model_state=true`, `step_path`, canonical creation coordinates, terminal-path metadata다.
- v1 terminal path는 matching corner만 허용한다: `A_cw_to_a`, `B_ccw_to_b` 같은 `<outer>_<cw|ccw>_to_<inner>` 형식.
- `void`는 copper 금지 keepout이며, generated copper box가 void와 면적으로 겹치면 즉시 실패한다.
- side-local fill은 left/right/top/bottom band별 pitch, trace, gap을 따로 파생한다.
- PCB layer 간 z 위치는 `layer_index * (pcb_thickness_mm + layer_gap_mm)`이고, `layer_gap_mm >= 2.0`을 강제한다.
- 이 prototype 단계는 EM 연결 없음, port/source 없음, solve 없음으로 고정한다.

## Affected Notes
- 관련 코드 노트: [[sdd/code/src/peetsfea/tx_rect_void.py]], [[sdd/code/entry/export_tx_rect_void_step.py]], [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]
- 관련 completed baseline: [[sdd/plans/0.2.22-type2-build123d-non-model-step]]
- 관련 전체 계획: [[sdd/plans/0.2.22-type2-step-to-em-validate-pipeline]]
- 관련 non-model import smoke: [[sdd/plans/0.2.22-type2-pyaedt-step-import]]
- 관련 문서: [[docs/tx-rect-void-step]]

## Acceptance
- `.venv/bin/python entry/export_tx_rect_void_step.py --seed 0`가 `run/step/tx_rect_void_coil.step`와 metadata JSON을 생성한다.
- metadata JSON은 modeled object identity, role, model_state, canonical coordinates, material, terminal-path metadata를 담는다.
- `../.venv/bin/pytest -q ../tests/tx_rect_void`가 통과한다.
- invalid TOML, invalid range, unsupported terminal path, layer gap below 2mm, copper/void overlap은 조용히 넘어가지 않고 예외를 발생시킨다.
