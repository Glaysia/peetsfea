---
title: type2-plate-stack
created: 2026-04-19 @ 21:20
updated: 2026-04-19 @ 21:20
tags:
  - type2
  - tx
  - rx
  - plate-stack
  - hfss
---

# Type2 Plate Stack

이 문서는 active type2 plate-stack family의 shared runtime boundary를 설명한다.
`tx_plate_stack`, `rx_plate_stack`는 scene/STEP ledger 단계의 modeled object role이지만,
current HFSS setup-ready/EM runtime은 아직 이 역할들을 처리하지 않는다.

## Shared Contract
- plate-stack roles: `tx_plate_stack`, `rx_plate_stack`
- plate-stack entries는 coil terminal reconstruction owner가 아니라 geometry/export owner다.
- current no-terminal sentinel은 `terminal_metadata = {"kind": "none"}`다.
- plate-stack roles는 port-sheet reconstruction, lumped-port assignment, endpoint extraction에
  직접 들어가면 안 된다.

## HFSS Runtime Boundary
- `peetsfea.backend.pyaedt.type2_step_setup_ready`는 plate-stack roles를 HFSS import/design
  work 시작 전에 reject한다.
- `assign_post_import_mesh`는 plate-stack roles를 명시적으로 reject한다.
- `assign_type2_lumped_ports`는 plate-stack roles를 명시적으로 reject한다.
- `build_type2_em_input`는 plate-stack roles를 명시적으로 reject한다.
- 따라서 current operator flow는 scene/STEP export와 artifact inspection에서 멈추며,
  dedicated plate-stack HFSS ownership은 아직 landing하지 않았다.

## Role Notes
- `tx_plate_stack`: active TX plate-stack는 `tx_region` full `YZ` footprint를 쓰고
  `tx_region.min_x`에 붙어 `+X` 방향으로 쌓인다. `tx_rect_void` coil-only runtime helper로
  보내면 안 된다.
- `rx_plate_stack`: active RX plate-stack direction이다. detailed RX geometry/body-order contract는
  [`docs/type2-rx-plate-stack.md`](type2-rx-plate-stack.md)에 있다.

## Legacy Coil Reference
- `tx_single_coil` / legacy `rx_single_coil` coil geometry reference는
  [`docs/tx-rect-void-step.md`](tx-rect-void-step.md)에 남아 있다.
- 그 문서는 legacy coil contract용이며, active TX/RX plate-stack contract 문서가 아니다.
