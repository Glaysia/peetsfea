from __future__ import annotations

from ansys.aedt.core import Hfss

from peetsfea.types.manifest import Manifest

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
    if name == "fr4_er":
        return str(float(value))
    return f"{float(value)}mm"


def _assign_design_variables(hfss: Hfss, manifest: Manifest) -> None:
    selected = manifest["selected_parameters"]
    for key, value in selected.items():
        if isinstance(value, (int, float)):
            hfss[_sanitize_var_name(f"spec_{key}")] = _var_expr(key, value)

    for group in manifest["selected_coil_groups"]:
        kind = group["kind"]
        hfss[_sanitize_var_name(f"group_{kind}_requested_count")] = _var_expr("requested_count", group["requested_count"])
        hfss[_sanitize_var_name(f"group_{kind}_selected_count")] = _var_expr("selected_count", group["selected_count"])
        hfss[_sanitize_var_name(f"group_{kind}_spacing_mm")] = _var_expr("spacing_mm", group["spacing_mm"])

    for geometry in manifest["selected_group_geometry"]:
        kind = geometry["kind"]
        hfss[_sanitize_var_name(f"group_geom_{kind}_turn_count_max")] = _var_expr("turn_count_max", geometry["turn_count_max"])
        hfss[_sanitize_var_name(f"group_geom_{kind}_band_ratio")] = _var_expr("band_ratio", geometry["band_ratio"])
        hfss[_sanitize_var_name(f"group_geom_{kind}_trace_mm")] = _var_expr("trace_mm", geometry["trace"])
        hfss[_sanitize_var_name(f"group_geom_{kind}_gap_mm")] = _var_expr("gap_mm", geometry["gap"])

    for pcb in manifest["selected_pcbs"]:
        pcb_id = _sanitize_var_name(pcb["id"])
        pos_x, pos_y, pos_z = pcb["position"]
        hfss[f"pcb_{pcb_id}_position_x_mm"] = _var_expr("position_x_mm", pos_x)
        hfss[f"pcb_{pcb_id}_position_y_mm"] = _var_expr("position_y_mm", pos_y)
        hfss[f"pcb_{pcb_id}_position_z_mm"] = _var_expr("position_z_mm", pos_z)
        hfss[f"pcb_{pcb_id}_rotation_deg"] = _var_expr("rotation_deg", pcb["rotation_deg"])
        hfss[f"pcb_{pcb_id}_present"] = "1" if pcb["present"] else "0"


