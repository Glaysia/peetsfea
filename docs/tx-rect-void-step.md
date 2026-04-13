# TX Rect/Void STEP Spec

This draft spec is a standalone build123d STEP authoring path. It does not use
the existing type1 PyAEDT/HFSS pipeline.

## Purpose
- Generate one TX rectangular spiral coil footprint.
- Represent the coil by an outer rectangle and a movable void keepout rectangle.
- Export active stacked PCB layers and copper as a STEP file for later manual
  Ansys import.

## TOML Contract
- `design.units` must be `"mm"`.
- `manufacturing.pcb_thickness_mm` and `manufacturing.copper_thickness_mm` are
  fixed positive millimeter values.
- `tx_coil.*.range` uses `[is_integer, start, end, count]`.
- `tx_coil.layer_count` resolves to 1, 2, or 3.
- `tx_coil.layer_gap_mm` must resolve to at least 2.0 mm.
- `tx_coil.void_*_over_*` fields define the void size and center as ratios of
  the realized outer dimensions.
- `tx_coil.margin_ratio` defines the minimum void-to-outer clearance as a ratio
  of the matching outer axis.
- `tx_coil.metal_fill_factor` defines the copper trace fraction in each
  side-local pitch cell.
- `tx_coil.terminal_path` supports `<outer>_<cw|ccw>_to_<inner>` where `A-D`
  are outer corners and `a-d` are matching void corners. v1 requires matching
  corners such as `A_cw_to_a`.

## Output
- The CLI `entry/export_tx_rect_void_step.py` writes a STEP file under
  `run/step/` by default.
- A metadata JSON file is written next to the STEP path and records realized
  parameters, bounds, layer positions, and generated box primitives.

## Out Of Scope
- PyAEDT, HFSS launch, AEDT import, ports, sources, and solving.
- Compatibility with legacy `tx_dd` and `tx_vertical` spec fields.
