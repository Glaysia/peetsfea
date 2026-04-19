---
title: test_sample_type2_entry.py
created: 2026-04-19 @ 17:35
updated: 2026-04-20 @ 12:18
tags:
  - tests
  - type2
  - sampling
---

# test_sample_type2_entry.py

## Source
- Path: `tests/type2/test_sample_type2_entry.py`
- Code note path: `sdd/code/tests/type2/test_sample_type2_entry.py.md`
- Direct owner: [[sdd/plans/0.2.22-type2-sampled-build-split]]
- Direct verification target: [[sdd/code/entry/sample.py]]
- Discovery bridge: [[sdd/code/tests/type2/test_build_type2_entry.py]]

## 역할
- sampled TOML, manifest metadata, sampled owner-path selection contract를 검증한다.
- sample entrypoint의 operator-facing progress/stage stdout contract를 검증한다.

## Canonical coverage
- active example uses `tx_plate_stack` + `rx_plate_stack`
- active example plate-stack PCB total uses a shared TX/RX baseline of `0.4 mm`
- sampled owner paths는 source order canonical 4-owner surface(`tx.turn_count`, `tx.metal_fill_factor`, `rx.turn_count`, `rx.metal_fill_factor`)를 따른다
- sampled TOML keeps plate scalar fields fixed
- sampled TOML keeps sampled `turn_count`, `metal_fill_factor` owners를 `count=1` scalar range로 freeze한다
- sampled TOML excludes removed `shoe_depth_mm` from both modeled payload and sampled metadata
- manifest identity and hash contract remain unchanged
- `MAKE_STEP_ON_SAMPLE=True` single-worker path emits coarse STEP stage lines around export.
- `MAKE_STEP_ON_SAMPLE=False` does not emit STEP stage lines and does not call the exporter.

## 변경 시 주의점
- sampled owner assertions를 role-blind coil field enumeration으로 되돌리지 않는다.
- stage-log assertions는 manifest JSON shape나 design identity contract를 대체하지 않는다.
