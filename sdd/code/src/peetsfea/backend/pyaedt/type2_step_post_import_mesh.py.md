---
title: type2_step_post_import_mesh.py
created: 2026-04-18 @ 09:09
updated: 2026-05-07 @ 00:00
tags:
  - em
  - pyaedt
---

# type2_step_post_import_mesh.py

## Source
- Path: `src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py`
- Code note path: `sdd/code/src/peetsfea/backend/pyaedt/type2_step_post_import_mesh.py.md`
- Status: active
- Primary graph owner: [type2-em-setup-boundary](../../../../../architecture/type2-em-setup-boundary.md)

## 역할
- STEP import 후 setup-ready mesh operation을 적용한다.
- `RxOnly` conductor-only mesh target and `TxRx` TX inner + RX conductor mesh targets을 소유한다.
- TX inner conductor names must be deterministic and role-specific; generic `tx_copper_*` matching is not sufficient.
- TxRx pair 길이/메시 해상도는 역할별 `canonical_coordinates.trace_width_mm`에서 계산한다.
- `rx_single_coil` 단독 모드에서는 RX 추적 폭만 사용한다.

## 입력 / 출력
- 입력: HFSS design, imported TX/RX conductor names, modeled `canonical_coordinates.trace_width_mm`, mesh policy
- 출력: `Length1` mesh operation (`MaxLength` 포함)

## Canonical state
- Mesh target set contains only RX conductor bodies in RxOnly and TX inner + RX conductor bodies in TxRx.
- `tx_region` and other non-modeled guide/context objects are never mesh targets.
- TX inner mesh lookup uses `tx_inner_copper_l*` / `tx_inner_copper_stack` explicitly; it does not fall back to `tx_copper_*`.
- `MaxLength` output format은 `f\"{value:.12g}mm\"`이며 값은 아래 규칙을 따른다.
  - RxOnly: `rx_trace_width_mm / 9.0`
  - TxRx: `sqrt(tx_trace_width_mm * rx_trace_width_mm) / 9.0`
- 요약/페이로드 모두 동일한 `MaxLength`를 사용한다.

## Invariants / fail-fast
- Missing RX or TX role-specific conductor target fails immediately with role and available names context.
- Unsupported TX role families are rejected before mesh assignment.
- `canonical_coordinates` table, `trace_width_mm` key, numeric 타입, finite 값, 양의값 검증이 실패하면 즉시 종료한다.
- PyAEDT mesh assignment false returns fail immediately.
- RxOnly must not include TX bodies in the mesh payload.
- `MESH_LENGTH_MAX_LENGTH = \"5mm\"` 고정값은 제거되었다.

## Helpers added
- `_required_canonical_coordinates`
- `_required_positive_finite_number`
- `_required_trace_width_mm`
- `_required_mesh_max_length_mm`

## Graph links
- Primary owner: [type2-em-setup-boundary](../../../../../architecture/type2-em-setup-boundary.md)
- Direct handoff: [type2_step_em_input.py](type2_step_em_input.py.md)
- Related plan: [0.2.24 Type2 Trace Width Mesh Length](../../../../../plans/0.2.24-type2-trace-width-mesh-length.md)
