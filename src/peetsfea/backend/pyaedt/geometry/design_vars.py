from __future__ import annotations

from pathlib import Path

from ansys.aedt.core import Hfss

from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver.constants import SCALAR_RANGE_SPECS
from peetsfea.spec.resolver.sampling import build_sampling_registry, is_sampling_entry_frozen, iter_registry_entries_in_canonical_order
from peetsfea.types.manifest import Manifest


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
    if name.endswith("_count") or name.endswith("turn_count_max") or name.endswith("requested_count") or name.endswith("selected_count"):
        return str(int(value))
    if name.endswith("_deg") or name.endswith("rotation_deg"):
        return f"{float(value)}deg"
    if name in {"fr4_er", "ferrite_relative_permeability"}:
        return str(float(value))
    return f"{float(value)}mm"


def _source_toml_path(manifest: Manifest) -> str:
    inputs = manifest["inputs"]
    return inputs.get("source_toml_path", inputs["toml_path"])


def _free_scalar_selected_values(manifest: Manifest) -> list[tuple[str, int | float | bool]]:
    selected = manifest["selected_parameters"]
    source_spec, _ = load_toml_bytes(path=Path(_source_toml_path(manifest)))
    registry = build_sampling_registry(source_spec)
    free_values: list[tuple[str, int | float | bool]] = []
    for entry in iter_registry_entries_in_canonical_order(registry):
        selected_key = _SELECTED_KEY_BY_OWNER_PATH.get(entry.owner_path)
        if selected_key is None:
            continue
        if is_sampling_entry_frozen(source_spec, entry):
            continue
        free_values.append((selected_key, selected[selected_key]))
    return free_values


def _assign_design_variables(hfss: Hfss, manifest: Manifest) -> None:
    for key, value in _free_scalar_selected_values(manifest):
        if isinstance(value, bool):
            hfss[_sanitize_var_name(f"spec_{key}")] = "1" if value else "0"
        elif isinstance(value, (int, float)):
            hfss[_sanitize_var_name(f"spec_{key}")] = _var_expr(key, value)
