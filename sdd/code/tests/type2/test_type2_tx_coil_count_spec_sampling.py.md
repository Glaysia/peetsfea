---
title: test_type2_tx_coil_count_spec_sampling.py
created: 2026-04-28 @ 19:40
updated: 2026-04-28 @ 19:40
tags:
  - test
  - type2
  - sampling
---

# test_type2_tx_coil_count_spec_sampling.py

## Source
- Path: `tests/type2/test_type2_tx_coil_count_spec_sampling.py`
- Code note path: `sdd/code/tests/type2/test_type2_tx_coil_count_spec_sampling.py.md`
- Status: active but xfailed while generic TX plate-stack contracts are inactive.

## Single Responsibility
- Records the older type2 TX plate-stack coil-count and array-x sampling contracts.
- Keeps the obsolete expectations visible without allowing them to fail the active RxOnly suite.

## Inputs / Outputs
- Inputs are test-local TOML strings with `tx_plate_stack`, `rx_plate_stack`, `tx_coil_count`, and `tx_array_x_usage_ratio`.
- Outputs are parser, resolver, and sampled-owner assertions when the generic TX plate-stack path is re-enabled.

## Canonical State
- The active parser rejects generic modeled TX roles in RxOnly mode before these historical sampling contracts can execute.
- `tx_inner_single_coil` is the supported geometry-only TX path for current type2 work.
- Xfailed generic TX/RX plate-stack local TOML keeps fixed singleton fields unchanged while lowering historical `turn_count`
  sweep ranges from `[true, 2, 5, 4]` to `[true, 2, 4, 3]`.

## Invariants
- Do not route active RxOnly builds through generic TX plate-stack parser/export behavior.
- If generic TX plate-stack support is restored, remove or narrow the module-level xfail and revalidate the sampled-owner order.

## Fail-Fast Points
- `load_type2_step_spec()` raises for unsupported generic TX roles in the active parser.
- Range canonicalization assertions should remain fail-fast if the role becomes supported again.

## Collaborators
- [type2_sampled.py](../../src/peetsfea/type2_sampled.py.md)
- [type2_step_spec.py](../../src/peetsfea/type2_step_spec.py.md)
- [0.2.24 Type2 Turn Count Sweep Upper Bound](../../../plans/0.2.24-type2-turn-count-sweep-upper-bound.md)

## Related Tests
- [test_generate_type2_step.py](test_generate_type2_step.py.md)

## Change Hazards
- Removing the xfail without re-enabling generic TX plate-stack parsing will reintroduce active RxOnly failures.
- Updating sampled-owner ordering requires synchronizing this module with manifest and dataset audit expectations.
