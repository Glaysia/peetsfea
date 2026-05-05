---
title: type2_sampled_skip.py
created: 2026-04-21 @ 00:00
updated: 2026-05-03 @ 00:00
tags:
  - sampling
  - manifest
---

# type2_sampled_skip.py

## Source
- Path: `src/peetsfea/type2_sampled_skip.py`
- Code note path: `sdd/code/src/peetsfea/type2_sampled_skip.py.md`
- Primary graph owner: [type2-sampled-module-boundary](../../../structure/type2-sampled-module-boundary.md)

## 역할
- Type2 sample manifest의 skipped seed ledger shape와 validation helpers를 소유한다.

## 입력 / 출력
- 입력: attempted seed, attempted sample index, failure phase, `ValueError`/`RuntimeError` exception object, raw manifest skipped payload.
- 출력: copied/validated skipped manifest entries.

## Canonical state
- skipped entry fields are `seed`, `sample_index`, `phase`, `error_type`, and `error_message`.
- `phase` is either `sample` or `step`.
- skipped entries describe failed attempted seeds only; successful design state remains in `manifest.entries`.

## Invariants / fail-fast
- skipped entry values must be concrete non-null runtime values.
- loader validation rejects malformed skipped entries immediately.
- this module accepts only the orchestration-approved skippable exception classes: `ValueError` and `RuntimeError`.

## 관련 테스트
- `tests/type2/test_sample_type2_entry.py`

## 변경 시 주의점
- Do not hide missing required skipped fields with mapping fallback APIs.
- Keep notebook/sample selection based on successful `entries`, not skipped ledger order.

## Graph links
- Primary owner: [type2-sampled-module-boundary](../../../structure/type2-sampled-module-boundary.md)
- Parent orchestration: [type2_sampled.py](type2_sampled.py.md)
- Entry consumer: [sample.py](../../entry/sample.py.md)
- Representative verification: [test_sample_type2_entry.py](../../tests/type2/test_sample_type2_entry.py.md)
