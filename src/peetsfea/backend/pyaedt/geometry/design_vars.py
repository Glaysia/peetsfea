from __future__ import annotations

from pathlib import Path
from typing import cast

from ansys.aedt.core import Hfss

from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver.constants import SCALAR_RANGE_SPECS
from peetsfea.spec.resolver.sampling import build_sampling_registry, is_sampling_entry_frozen, iter_registry_entries_in_canonical_order
from peetsfea.types.manifest import GroupGeometryParams, Manifest, ResolvedCoilGroup


_SELECTED_KEY_BY_OWNER_PATH: dict[str, str] = {path: key for path, key, _ in SCALAR_RANGE_SPECS}


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
        name.endswith("_count")
        or name.endswith("count_mode")
        or name.endswith("count_range")
        or name.endswith("turn_count_max")
        or name.endswith("requested_count")
        or name.endswith("selected_count")
    ):
        return str(int(value))
    if name.endswith("_deg") or name.endswith("rotation_deg"):
        return f"{float(value)}deg"
    if name in {"fr4_er", "ferrite_relative_permeability"}:
        return str(float(value))
    return f"{float(value)}mm"


def _source_toml_path(manifest: Manifest) -> str:
    inputs = manifest["inputs"]
    return inputs.get("source_toml_path", inputs["toml_path"])


def _coil_group_by_kind(manifest: Manifest) -> dict[str, ResolvedCoilGroup]:
    return {entry["kind"]: entry for entry in manifest["selected_coil_groups"]}


def _group_geometry_by_kind(manifest: Manifest) -> dict[str, GroupGeometryParams]:
    return {entry["kind"]: entry for entry in manifest["selected_group_geometry"]}


def _selected_value_for_owner_path(manifest: Manifest, owner_path: str) -> int | float | bool:
    selected = manifest["selected_parameters"]
    scalar_key = _SELECTED_KEY_BY_OWNER_PATH.get(owner_path)
    if scalar_key is not None:
        return selected[scalar_key]

    group_by_kind = _coil_group_by_kind(manifest)
    if owner_path == "coil_groups[0].count_mode":
        return int(group_by_kind["tx_dd"]["requested_count"])
    if owner_path == "coil_groups[1].count_range":
        return int(group_by_kind["tx_vertical"]["requested_count"])

    geometry_by_kind = _group_geometry_by_kind(manifest)
    if owner_path.startswith("coil_groups_params."):
        _, kind, field_name = owner_path.split(".", 2)
        geometry = geometry_by_kind[kind]
        return cast(int | float, geometry[field_name])  # turn_count_max/band_ratio/metal_ratio only

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
