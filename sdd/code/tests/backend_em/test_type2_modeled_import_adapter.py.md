---
title: test_type2_modeled_import_adapter.py
created: 2026-04-19 @ 17:35
updated: 2026-04-19 @ 23:59
tags:
  - tests
  - backend-em
  - import-only
---

# test_type2_modeled_import_adapter.py

## Source
- Path: `tests/backend_em/test_type2_modeled_import_adapter.py`
- Code note path: `sdd/code/tests/backend_em/test_type2_modeled_import_adapter.py.md`

## 역할
- modeled import adapter가 coil metadata와 plate-stack `stub_port` metadata를 role-aware로 파싱하는지 검증한다.

## Canonical coverage
- `tx_plate_stack` / `rx_plate_stack` accept `terminal_metadata.kind = "stub_port"`
- plate-stack metadata는 reconstructed `tx_port_sheet` / `rx_port_sheet` 입력 shape를 유지한다.
- coil roles still require full terminal metadata
- malformed `stub_port` metadata or mixed role metadata is rejected
- fixture canonical coordinates keep TX/RX coil copper Z baselines aligned at `0.4 mm`

## 변경 시 주의점
- geometry-only role rejection expectation을 import-only acceptance expectation으로 갱신해야 한다.
- direct EM input helper 지원 여부는 이 테스트의 범위가 아니며, plate-stack은 setup-ready facade 경로에서만 boundary/explicit ports/save를 검증한다.
