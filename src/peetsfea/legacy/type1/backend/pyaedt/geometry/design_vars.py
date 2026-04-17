from __future__ import annotations

from pathlib import Path
from typing import cast

from peetsfea.aedt import Hfss

from peetsfea.spec.loader import load_toml_bytes
from peetsfea.legacy.type1.spec.resolver.constants import SCALAR_RANGE_SPECS
from peetsfea.legacy.type1.spec.resolver.sampling import build_sampling_registry, is_sampling_entry_frozen, iter_registry_entries_in_canonical_order
from peetsfea.types.manifest import GroupGeometryParams, Manifest, ResolvedCoilGroup
from peetsfea.types.runtime_selection import coil_group_requested_count


_SELECTED_KEY_BY_OWNER_PATH: dict[str, str] = {path: key for path, key, _ in SCALAR_RANGE_SPECS}
_GEOMETRY_KIND_BY_OWNER_KIND: dict[str, str] = {
    "neo_tx_dd": "tx_dd",
    "neo_tx_vertical": "tx_vertical",
    "rx_dd": "rx_dd",
}


def _sanitize_var_name(name: str) -> str:
    chars: list[str] = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            chars.append(ch)
        else:
            chars.append("_")
    return "".join(chars).strip("_")


def _var_expr(name: str, value: int | float | str) -> str:
    if isinstance(value, str):
        return value
    if (
        name.endswith("orientation_mode")
        or name.endswith("corner_mode")
        or name.endswith("_count")
        or name.endswith("stacked_mode")
        or name.endswith("count_range")
        or name.endswith("turn_count")
        or name.endswith("requested_count")
        or name.endswith("selected_count")
    ):
        return str(int(value))
    if name.endswith("_deg") or name.endswith("rotation_deg"):
        return f"{float(value)}deg"
    if name in {"fr4_er", "ferrite_relative_permeability"}:
        return str(float(value))
    if (
        name.endswith("_ratio_to_tx_dd_center")
        or name.endswith("_ratio_to_neo_tx_dd_center")
        or name.endswith("_pair_spacing_ratio")
        or name.endswith("metal_ratio")
        or name.endswith("band_ratio")
    ):
        return str(float(value))
    return f"{float(value)}mm"


def _source_toml_path(manifest: Manifest) -> str:
    inputs = manifest["inputs"]
    if "source_toml_path" in inputs:
        return inputs["source_toml_path"]
    return inputs["toml_path"]


def _coil_group_by_kind(manifest: Manifest) -> dict[str, ResolvedCoilGroup]:
    return {entry["kind"]: entry for entry in manifest["selected_coil_groups"]}


def _group_geometry_by_kind(manifest: Manifest) -> dict[str, GroupGeometryParams]:
    return {entry["kind"]: entry for entry in manifest["selected_group_geometry"]}


def _selected_value_for_owner_path(manifest: Manifest, owner_path: str) -> int | float | bool:
    selected = manifest["selected_parameters"]
    if owner_path in _SELECTED_KEY_BY_OWNER_PATH:
        scalar_key = _SELECTED_KEY_BY_OWNER_PATH[owner_path]
        return selected[scalar_key]

    group_by_kind = _coil_group_by_kind(manifest)
    if owner_path == "coil_groups[0].stacked_mode":
        return int(group_by_kind["tx_dd"]["layer_count"]) - 1
    if owner_path == "coil_groups[1].count_range":
        return coil_group_requested_count(group_by_kind["tx_vertical"])

    geometry_by_kind = _group_geometry_by_kind(manifest)
    if owner_path.startswith("coil_groups_params."):
        _, owner_kind, field_name = owner_path.split(".", 2)
        assert owner_kind in _GEOMETRY_KIND_BY_OWNER_KIND, f"Unsupported geometry owner kind in AEDT design vars: {owner_kind}"
        geometry_kind = _GEOMETRY_KIND_BY_OWNER_KIND[owner_kind]
        geometry = geometry_by_kind[geometry_kind]
        return cast(int | float, geometry[field_name])  # turn_count/band_ratio/metal_ratio only

    raise ValueError(f"Unsupported AEDT design variable owner path: {owner_path}")


def _free_input_owner_values(manifest: Manifest) -> list[tuple[str, int | float | bool]]:
    source_spec, _ = load_toml_bytes(path=Path(_source_toml_path(manifest)))
    registry = build_sampling_registry(source_spec)
    free_values: list[tuple[str, int | float | bool]] = []
    for entry in iter_registry_entries_in_canonical_order(registry):
        if is_sampling_entry_frozen(source_spec, entry):
            continue
        free_values.append((entry.owner_path, _selected_value_for_owner_path(manifest, entry.owner_path)))
    return free_values


def _assign_design_variables(hfss: Hfss, manifest: Manifest) -> None:
    for owner_path, value in _free_input_owner_values(manifest):
        variable_name = _sanitize_var_name(owner_path)
        if isinstance(value, bool):
            hfss[variable_name] = "1" if value else "0"
        elif isinstance(value, (int, float)):
            hfss[variable_name] = _var_expr(owner_path, value)
