from __future__ import annotations

import math
from typing import Literal, cast

from peetsfea.spec.loader import TOMLTable, require_table
from peetsfea.types.manifest import GroupGeometryParams, SelectedParameters

from ..constants import GROUP_GEOMETRY_OFFSET_BASE, GROUP_KIND_ORDER
from ..sampling import select_range_value
from ..types import SamplingContext

_PUBLIC_GEOMETRY_KEY_BY_KIND: dict[str, str] = {
    "tx_dd": "neo_tx_dd",
    "tx_vertical": "neo_tx_vertical",
    "rx_dd": "rx_dd",
}


def max_feasible_turns(outer: float, trace: float, gap: float) -> int:
    pitch = trace + gap
    if pitch <= 0:
        return 0
    raw = (outer + (2.0 * gap)) / (2.0 * pitch)
    return max(0, int(math.floor(raw - 1e-12)))


def resolve_group_geometry(
    spec: TOMLTable,
    seed: int,
    attempt: int,
    context: SamplingContext,
    selected_params: SelectedParameters,
) -> list[GroupGeometryParams]:
    assert "coil_groups_params" in spec, "spec must contain coil_groups_params"
    groups_table = require_table(spec["coil_groups_params"], "coil_groups_params")
    required_kinds = set(_PUBLIC_GEOMETRY_KEY_BY_KIND.values())
    if set(groups_table.keys()) != required_kinds:
        raise ValueError("coil_groups_params must contain exactly {neo_tx_dd, neo_tx_vertical, rx_dd}")

    selected_geometry: list[GroupGeometryParams] = []
    for idx, kind in enumerate(GROUP_KIND_ORDER):
        public_key = _PUBLIC_GEOMETRY_KEY_BY_KIND[kind]
        kind_root = f"coil_groups_params.{public_key}"
        assert public_key in groups_table, f"coil_groups_params must contain {public_key}"
        kind_table = require_table(groups_table[public_key], kind_root)
        if set(kind_table.keys()) != {"turn_count", "band_ratio", "metal_ratio"}:
            raise ValueError(f"{kind_root} must contain only ['turn_count', 'band_ratio', 'metal_ratio']")

        offset = GROUP_GEOMETRY_OFFSET_BASE + (idx * 10)
        turns = select_range_value(
            spec, f"{kind_root}.turn_count", expect_integer=True, seed=seed, offset=offset, attempt=attempt, context=context
        )
        band_ratio = select_range_value(
            spec,
            f"{kind_root}.band_ratio",
            expect_integer=False,
            seed=seed,
            offset=offset + 1,
            attempt=attempt,
            context=context,
        )
        metal_ratio = select_range_value(
            spec,
            f"{kind_root}.metal_ratio",
            expect_integer=False,
            seed=seed,
            offset=offset + 2,
            attempt=attempt,
            context=context,
        )
        n_turns = int(turns)
        band_ratio_float = float(band_ratio)
        ratio = float(metal_ratio)
        if n_turns < 1:
            raise ValueError(f"{kind_root}.turn_count must be >= 1")
        if n_turns > 9:
            raise ValueError(f"{kind_root}.turn_count must be <= 9")
        if band_ratio_float <= 0 or band_ratio_float >= 1:
            raise ValueError(f"{kind_root}.band_ratio must be > 0 and < 1")
        if ratio <= 0 or ratio >= 1:
            raise ValueError(f"{kind_root}.metal_ratio must be > 0 and < 1")
        if kind == "tx_dd":
            outer_x = float(selected_params["tx_dd_outer_x"])
            outer_y = float(selected_params["tx_dd_outer_y"])
        elif kind == "tx_vertical":
            outer_x = float(selected_params["tx_vertical_outer_x"])
            outer_y = float(selected_params["tx_vertical_outer_y"])
        else:
            outer_x = float(selected_params["rx_dd_outer_x"])
            outer_y = float(selected_params["rx_dd_outer_y"])
        effective_outer_y = min(outer_y, float(selected_params["tx_region_vertical_z_mm"])) if kind == "tx_vertical" else outer_y
        base_outer = min(outer_x, effective_outer_y)
        if base_outer <= 0:
            raise ValueError(f"{kind_root}.base_outer (derived) must be > 0")
        band_mm = band_ratio_float * base_outer
        pitch = band_mm / float(n_turns)
        trace = pitch * ratio
        gap = pitch * (1.0 - ratio)
        if trace <= 0:
            raise ValueError(f"{kind_root}.trace (derived) must be > 0")
        if gap < 0:
            raise ValueError(f"{kind_root}.gap (derived) must be >= 0")
        selected_geometry.append(
            {
                "kind": cast(Literal["tx_dd", "tx_vertical", "rx_dd"], kind),
                "turn_count": n_turns,
                "band_ratio": band_ratio_float,
                "metal_ratio": ratio,
                "trace": trace,
                "gap": gap,
            }
        )
    return selected_geometry
