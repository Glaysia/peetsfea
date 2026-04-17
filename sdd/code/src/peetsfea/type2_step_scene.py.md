---
title: type2_step_scene.py
created: 2026-04-17 @ 09:09
updated: 2026-04-17 @ 20:08
tags:
  - type2
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
- single-coil scene assembly가 current two-sheet contract를 실제로 소유하고, `tx_port_sheet` / `rx_port_sheet`를 modeled STEP child로 coil과 같은 world frame에 배치한다.
- upstream single-coil scene이 이미 port sheet child를 제공하더라도, 이 모듈이 stub-to-stub bridging rule로 다시 canonicalize한 face를 최종 child set에 넣는다.

## 입력 / 출력
- 입력: parsed type2 specs + owner region specs + seed
- 출력: non-model scene entry/shape tuple, modeled scene child-shapes + modeled scene metadata

## Canonical state
- canonical scene geometry는 single `type2_scene.step` body set이다.
- modeled placement truth는 owner region canonical coordinates에서 derive된 export-time absolute placement다.
- modeled body set에는 PCB, copper, 그리고 exact-name port sheet body 하나가 coil별로 포함된다.
- current type2 single-coil scene exports exactly two such sheet bodies total: one TX and one RX.
- port-sheet geometry canonical owner는 transformed terminal-stub bottom-face square pair이며 terminal anchor span이나 single-square ownership은 더 이상 sheet shape owner가 아니다.
- canonical diagonal selection은 두 stub center를 잇는 inter-stub centerline에 대해 각 square의 두 diagonal 중 perpendicular distance 합을 최대화하는 쪽을 고르는 widened rule이다.

## Invariants / fail-fast
- legacy multi-step/object directory outputs는 여기서 다시 만들지 않는다.
- role plane and owner plane must match
- modeled bbox must fit owner bounds before export
- modeled scene child body names must be unique
- port sheet body names must remain unique and must stay separate top-level STEP children.
- current scene-layer port sheet derivation must use exactly the two terminal-stub bottom-face squares for the coil.
- in the single-layer path, the sheet face must stay in the shared plane parallel to those stub bottom faces.
- the canonical boundary uses one deterministic diagonal from each stub bottom-face square and bridges those two diagonals into one sheet face.
- diagonal choice is not arbitrary: each stub square must choose the diagonal whose two endpoints maximize the sum of perpendicular distances to the inter-stub centerline in the shared bottom-face plane.
- if propagated upstream port-sheet geometry disagrees with that rule, this module replaces it before export metadata/scene children escape the module.

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
- port-sheet placement는 두 terminal stub의 bottom-face square pair에서 derive해야 하고 owner-region heuristic, terminal-pair span, single-square ownership으로 대체하면 안 된다.
- widened diagonal rule은 stub-center centerline 기준으로 계산해야 하며, 좁은 대각선이나 임의의 고정 corner pair를 쓰면 안 된다.
- port sheet를 non-model member로 재분류하지 않는다. modeled object exact-name set 안에서 유지해야 한다.
- terminal stub footprint pair가 square가 아니거나 positive area가 아니면 fail-fast해야 한다.
- terminal stub pair가 exactly two가 아니거나 shared bottom-face plane을 이루지 않으면 fail-fast해야 한다.

## Links
- [[sdd/code/src/peetsfea/type2_step_ledger.py]]
- [[sdd/code/src/peetsfea/type2_step_export.py]]
