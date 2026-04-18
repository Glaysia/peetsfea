---
title: type2_step_scene.py
created: 2026-04-17 @ 09:09
updated: 2026-04-18 @ 18:46
tags:
  - step-export
---

# type2_step_scene.py

## Source
- Path: `src/peetsfea/type2_step_scene.py`
- Code note path: `sdd/code/src/peetsfea/type2_step_scene.py.md`
- Status: active
- Related plan: [[sdd/plans/0.2.22-src-entry-800-line-refactor-threshold]]
- Parent note: [[sdd/code/entry/generate_type2_step.py]]

## 역할
- non-model build123d shapes, single-coil placement offsets, final scene body assembly를 담당한다.
- modeled canonical coordinates/terminal metadata를 geometry에서 직접 계산해 export layer로 전달한다.
- single-coil scene assembly가 PCB/copper STEP child set과 optional TX/RX underlay tri-layer STEP child set을 소유하고, port sheet는 STEP body로 내보내지 않고 metadata vertices로만 export한다.
- upstream single-coil scene이 port sheet child를 제공하더라도, 이 모듈은 그것을 final STEP child set에서 제외하고 stub-to-stub bridging rule의 canonical vertices만 metadata로 남긴다.
- 0.2.23 document contract에서는 `underlay_repeat_count`가 non-zero인 TX/RX modeled object에 대해 explicit ferrite / PET_PSA / air slabs를 scene layer에서만 추가한다. 이 underlay는 `tx_rect_void` core geometry decomposition이 아니라 type2 scene placement/body taxonomy의 책임이다.

## 입력 / 출력
- 입력: parsed type2 specs + owner region specs + seed
- 출력: non-model scene entry/shape tuple, modeled scene child-shapes + modeled scene metadata

## Canonical state
- canonical scene geometry는 single `type2_scene.step` body set이다.
- modeled placement truth는 owner region canonical coordinates에서 derive된 export-time absolute placement다.
- `tx_single_coil` canonical placement는 `tx_region.min_x` touch + centered Y + owner max-Z touch다.
- modeled body set에는 PCB/copper와 optional TX/RX underlay slabs만 포함된다.
- terminal metadata는 start/end plane points뿐 아니라 canonical `port_sheet_vertices_xyz`도 포함해 downstream HFSS sheet reconstruction source가 된다.
- current type2 single-coil scene does not export port-sheet bodies into `type2_scene.step`; TX/RX sheets exist only as metadata-driven reconstruction targets.
- underlay body owner는 one-site stack이며, per-layer PCB/copper body set 아래에 layer-by-layer로 복제되지 않는다.
- TX underlay footprint canonical source는 `tx_region` full `XY` bounds다.
- RX underlay footprint canonical source는 `rx_region_max` full `YZ` bounds다.
- TX underlay unit order는 `MULL12060ferrite` 0.20 mm -> `PET_PSA` 0.15 mm -> explicit `vacuum` air body 0.02 mm이며, `u0`가 TX에 가장 가까운 첫 unit이다.
- TX underlay exact names는 `tx_underlay_ferrite_u{n}`, `tx_underlay_pet_psa_u{n}`, `tx_underlay_air_u{n}` order로 append된다.
- RX underlay exact names는 `under_rx_ferrite_u{n}`, `under_rx_pet_psa_u{n}`, `under_rx_air_u{n}` order로 append된다.
- RX underlay는 `rx_region_max`의 `-X` boundary에 anchor하고, coil-facing material은 ferrite다. 따라서 physical `-X -> +X` order는 `air -> PET_PSA -> ferrite`다.
- new underlay exact object/body names는 feature-local rule로 `<= 32` chars여야 한다.
- port-sheet geometry canonical owner는 transformed start/end bottom-face square pair이며 terminal anchor span이나 single-square ownership은 더 이상 sheet shape owner가 아니다.
- TX는 layer count와 무관하게 transformed vertical-bus bottom-face square pair를 canonical owner로 쓰고, single-layer TX도 one-layer terminal-stub column에서 같은 bus footprint를 합성한다. RX는 transformed terminal-stub bottom-face square pair를 쓴다.
- canonical diagonal selection은 두 stub center를 잇는 inter-stub centerline에 대해 각 square의 두 diagonal 중 perpendicular distance 합을 최대화하는 쪽을 고르는 widened rule이다.

## Invariants / fail-fast
- legacy multi-step/object directory outputs는 여기서 다시 만들지 않는다.
- role plane and owner plane must match
- modeled bbox must fit owner bounds before export
- TX exported modeled bbox minimum-X는 `tx_region.min_x`에 닿아야 하고 centered-X로 drift하면 안 된다.
- modeled scene child body names must be unique
- TX/RX `underlay_repeat_count` resolved value는 `{0, 2, 4, 6, 8}` contract를 따른다.
- TX underlay first ferrite top face는 modeled object canonical minimum-Z plane보다 `underlay_gap_mm`만큼 아래에 와야 하며, every later slab는 같은 semantic tri-layer order로 stack된다.
- RX underlay first exported unit must start on the owner `-X` boundary and consume owner thickness toward `+X` without changing RX coil max-X placement.
- TX underlay air 20 um와 RX underlay air 20 um는 spacing-only gap이 아니라 explicit exported `vacuum` body여야 한다.
- TX/RX underlay footprint는 coil bounds가 아니라 owner region full bounds를 canonical source로 삼는다.
- RX underlay semantic exported body order는 `ferrite -> pet_psa -> air`를 유지한다.
- current scene-layer port sheet derivation must use exactly one explicit start/end owner pair for the coil.
- the canonical sheet polygon must stay in the shared plane parallel to those owner bottom faces.
- the canonical boundary uses one deterministic diagonal from each owner bottom-face square and bridges those two diagonals into one metadata-owned sheet polygon.
- diagonal choice is not arbitrary: each stub square must choose the diagonal whose two endpoints maximize the sum of perpendicular distances to the inter-stub centerline in the shared bottom-face plane.
- exported terminal metadata must preserve the four canonical world-frame port-sheet vertices so HFSS import runtime can recreate the sheet without trusting STEP free-surface names.
- if propagated upstream port-sheet geometry disagrees with that rule, this module replaces it before export metadata escapes the module.

## 직접 의존
- [[sdd/code/src/peetsfea/type2_step_spec.py]]
- [[sdd/code/src/peetsfea/tx_rect_void.py]]
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]

## 이 파일을 쓰는 곳
- [[sdd/code/src/peetsfea/type2_step_export.py]]

## 관련 테스트
- [[sdd/code/tests/type2/test_generate_type2_step.py]]

## 변경 시 주의점
- scene assembly와 ledger writing을 다시 결합하지 않는다.
- placement math 변경은 import pipeline owner-fit validation과 함께 갱신해야 한다.
- underlay를 `tx_rect_void` core geometry 책임으로 밀어 넣지 않는다. TX/RX coil body taxonomy와 role-aware underlay scene taxonomy를 분리 유지한다.
- port-sheet placement는 canonical start/end owner bottom-face square pair에서 derive해야 하고 owner-region heuristic, terminal-pair span, single-square ownership으로 대체하면 안 된다.
- widened diagonal rule은 stub-center centerline 기준으로 계산해야 하며, 좁은 대각선이나 임의의 고정 corner pair를 쓰면 안 된다.
- port sheet를 non-model member로 재분류하지 않는다. STEP body로는 export하지 않더라도 modeled object terminal metadata ownership 아래 유지해야 한다.
- underlay bodies도 non-model member가 아니다. exact modeled body names/count 계약 아래에 둔다.
- terminal stub footprint pair가 square가 아니거나 positive area가 아니면 fail-fast해야 한다.
- canonical owner pair가 exactly two가 아니거나 shared bottom-face plane을 이루지 않으면 fail-fast해야 한다.
- canonical port-sheet vertices와 exported STEP face geometry가 drift하면 import-side reconstruction과 viewer/debug contracts가 함께 깨지므로 같은 rule source를 유지해야 한다.

## Links
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
