# TX Rect/Void STEP Generator

상위 정책은 [[SDD]], 전체 허브는 [[sdd/sdd-index]], 계획 허브는 [[sdd/plans/sdd-plans-index]]다.

## Goal
- 기존 PyAEDT/type1 TX DD 경로를 건드리지 않고, 단일 TX rectangular/void coil을 build123d STEP으로 내보내는 독립 authoring path를 만든다.
- TOML을 SSOT로 삼아 외곽 사각형, movable void keepout, side-local fill, 1-3 stacked PCB layer를 결정론적으로 실현한다.

## Scope
- 포함:
  - [[sdd/code/src/peetsfea/tx_rect_void.py]]
  - [[sdd/code/entry/export_tx_rect_void_step.py]]
  - [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]
  - `examples/tx_rect_void/tx_rect_void_coil.toml`
  - [[docs/tx-rect-void-step]]
- 제외:
  - 기존 type1 resolver/backend 연결
  - AEDT import, HFSS launch, EM ports, source assignment, solve
  - legacy `tx_dd` / `tx_vertical` migration

## Decisions
- STEP 생성은 `build123d`를 사용하고, 출력 기본 위치는 `run/step/`다.
- v1 terminal path는 matching corner만 허용한다: `A_cw_to_a`, `B_ccw_to_b` 같은 `<outer>_<cw|ccw>_to_<inner>` 형식.
- `void`는 copper 금지 keepout이며, generated copper box가 void와 면적으로 겹치면 즉시 실패한다.
- side-local fill은 left/right/top/bottom band별 pitch, trace, gap을 따로 파생한다.
- PCB layer 간 z 위치는 `layer_index * (pcb_thickness_mm + layer_gap_mm)`이고, `layer_gap_mm >= 2.0`을 강제한다.

## Affected Notes
- 관련 코드 노트: [[sdd/code/src/peetsfea/tx_rect_void.py]], [[sdd/code/entry/export_tx_rect_void_step.py]], [[sdd/code/tests/tx_rect_void/test_tx_rect_void.py]]
- 관련 기존 STEP 선례: [[sdd/code/examples/type2/generate_non_model_step.py]]
- 관련 문서: [[docs/tx-rect-void-step]]

## Acceptance
- `.venv/bin/python entry/export_tx_rect_void_step.py --seed 0`가 `run/step/tx_rect_void_coil.step`와 metadata JSON을 생성한다.
- `../.venv/bin/pytest -q ../tests/tx_rect_void`가 통과한다.
- invalid TOML, invalid range, unsupported terminal path, layer gap below 2mm, copper/void overlap은 조용히 넘어가지 않고 예외를 발생시킨다.

## Links
- [[SDD]]
- [[AGENTS]]
- [[CODE_COMMANDMENTS]]
- [[sdd/sdd-index]]
- [[sdd/plans/sdd-plans-index]]
