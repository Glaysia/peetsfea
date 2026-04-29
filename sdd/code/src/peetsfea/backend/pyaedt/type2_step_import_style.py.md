---
title: type2_step_import_style.py
created: 2026-04-18 @ 09:09
updated: 2026-04-29 @ 00:00
tags:
  - import
  - pyaedt
---

# type2_step_import_style.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_import_style.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_import_style.py.md`
- Status: active

## 역할
- Imported RX conductor/context objects에 material/color/name styling을 적용한다.
- Imported TX inner/RX conductor/context objects에 material/color/name styling을 적용한다.
- TX inner and RX port sheet reconstruction support remains runtime metadata, not imported STEP geometry.
- TxRx mode에서 TX inner의 port sheet는 모델 입력 `terminal_metadata`의 `port_sheet_vertices_xyz`를 사용해
  `tx_inner_port_sheet`로 재구성한다.

## 입력 / 출력
- 입력: partitioned imported object groups, HFSS modeler
- 출력: styled imported objects and runtime reconstructed TX inner/RX sheet geometry where needed

## Canonical state
- RX conductor receives conductor material/styling.
- Non-modeled guide/context objects remain non-conductor context.
- RxOnly creates no TX reconstructed sheets.
- TxRx 생성 시 TX 내측 코일은 `tx_inner_port_sheet`로 재구성되며, RX는 기존 `rx_port_sheet`를 사용한다.
- TX 내측(port) 역할은 `tx_inner_single_coil`으로만 처리하며, 일반 `tx_single_coil`는 이 경로에서 제외한다.

## Invariants / fail-fast
- Missing required RX imported objects fail immediately.
- Styling false returns fail immediately.
- Guide/context bodies must not be treated as conductor bodies.
- `tx_inner_single_coil`는 `terminal_metadata.port_sheet_vertices_xyz` 필수이며 누락·형식 오류는 즉시 실패한다.

## Collaborators
- [type2_step_import_core.py](type2_step_import_core.py.md)
- [type2_step_port_assignment.py](type2_step_port_assignment.py.md)
