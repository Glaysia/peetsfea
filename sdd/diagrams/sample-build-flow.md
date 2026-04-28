---
title: Sample Build Flow
created: 2026-04-17 @ 09:09
updated: 2026-04-28 @ 00:00
tags:
  - diagram
  - sampling
---

# Sample Build Flow

```mermaid
flowchart TD
    Source["type2 source TOML"]
    Sample["sample entry"]
    Sampled["sampled TOML + manifest"]
    Export["RX STEP export"]
    Import["import-only or setup-ready"]
    RxOnly["RxOnly mesh + RX port + RX reports"]

    Source --> Sample
    Sample --> Sampled
    Sampled --> Export
    Export --> Import
    Import --> RxOnly
```

## Notes
- TX shape-specific flow details were removed for the 0.2.24 reset.
- `tx_region` may remain as guide context only.
- Report variables are owned by [type2-em-report-contract](../architecture/type2-em-report-contract.md).
