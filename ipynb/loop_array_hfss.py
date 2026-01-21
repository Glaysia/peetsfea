#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, cast

from ansys.aedt.core.modeler.modeler_3d import Modeler3D
from pyaedt import Hfss


@dataclass(frozen=True)
class LoopArrayParams:
    L_outer: float = 200.0
    w_trace: float = 5.0
    t_cu: float = 0.035
    t_sub: float = 1.6
    g_loop: float = 10.0
    m_edge: float = 15.0
    g_cap: float = 1.5
    pad_len: float = 6.0
    pad_wid: float = 5.0


@dataclass(frozen=True)
class LoopBuildResult:
    pcb_size: float
    loop_names: list[str]
    pad_names: list[str]
    centers: list[tuple[float, float]]


def mm(value: float) -> str:
    return f"{value}mm"


def set_design_variables(hfss: Hfss, params: LoopArrayParams) -> None:
    hfss["L_outer"] = mm(params.L_outer)
    hfss["w_trace"] = mm(params.w_trace)
    hfss["t_cu"] = mm(params.t_cu)
    hfss["t_sub"] = mm(params.t_sub)
    hfss["g_loop"] = mm(params.g_loop)
    hfss["m_edge"] = mm(params.m_edge)
    hfss["g_cap"] = mm(params.g_cap)
    hfss["pad_len"] = mm(params.pad_len)
    hfss["pad_wid"] = mm(params.pad_wid)
    hfss["pitch"] = "L_outer + g_loop"
    hfss["pcb_size"] = "3*pitch + L_outer + 2*m_edge"


def validate_params(params: LoopArrayParams) -> None:
    if params.L_outer <= 0:
        raise ValueError("L_outer must be positive.")
    if params.w_trace <= 0 or params.w_trace >= params.L_outer / 2:
        raise ValueError("w_trace must be positive and less than L_outer/2.")
    if params.t_cu <= 0 or params.t_sub <= 0:
        raise ValueError("t_cu and t_sub must be positive.")
    if params.g_loop < 0 or params.m_edge < 0 or params.g_cap < 0:
        raise ValueError("g_loop, m_edge, and g_cap must be non-negative.")
    if params.pad_len <= 0 or params.pad_wid <= 0:
        raise ValueError("pad_len and pad_wid must be positive.")
    if params.g_cap + 2 * params.pad_len >= params.L_outer:
        raise ValueError("g_cap + 2*pad_len must be less than L_outer.")


def create_substrate(modeler: Modeler3D) -> None:
    modeler.create_box(
        origin=["-pcb_size/2", "-pcb_size/2", "-t_sub"],
        sizes=["pcb_size", "pcb_size", "t_sub"],
        name="substrate",
        material="FR4_epoxy",
    )


def create_loop(modeler: Modeler3D, i: int, j: int) -> tuple[str, str, str]:
    x_c = f"({i} - 1.5)*pitch"
    y_c = f"({j} - 1.5)*pitch"
    z0 = "0"
    loop_name = f"loop_{i}_{j}"

    top = modeler.create_box(
        origin=[f"{x_c} - L_outer/2", f"{y_c} + L_outer/2 - w_trace", z0],
        sizes=["L_outer", "w_trace", "t_cu"],
        name=loop_name,
        material="copper",
    )
    bottom = modeler.create_box(
        origin=[f"{x_c} - L_outer/2", f"{y_c} - L_outer/2", z0],
        sizes=["L_outer", "w_trace", "t_cu"],
        name=f"{loop_name}_bottom",
        material="copper",
    )
    left = modeler.create_box(
        origin=[f"{x_c} - L_outer/2", f"{y_c} - L_outer/2", z0],
        sizes=["w_trace", "L_outer", "t_cu"],
        name=f"{loop_name}_left",
        material="copper",
    )
    right_upper = modeler.create_box(
        origin=[f"{x_c} + L_outer/2 - w_trace", f"{y_c} + g_cap/2 + pad_len", z0],
        sizes=["w_trace", "(L_outer/2) - (g_cap/2 + pad_len)", "t_cu"],
        name=f"{loop_name}_right_upper",
        material="copper",
    )
    right_lower = modeler.create_box(
        origin=[f"{x_c} + L_outer/2 - w_trace", f"{y_c} - L_outer/2", z0],
        sizes=["w_trace", "(L_outer/2) - (g_cap/2 + pad_len)", "t_cu"],
        name=f"{loop_name}_right_lower",
        material="copper",
    )

    modeler.unite([top.name, bottom.name, left.name, right_upper.name, right_lower.name])

    pad_a = f"padA_{i}_{j}"
    pad_b = f"padB_{i}_{j}"
    modeler.create_box(
        origin=[f"{x_c} + L_outer/2 - pad_wid", f"{y_c} + g_cap/2", z0],
        sizes=["pad_wid", "pad_len", "t_cu"],
        name=pad_a,
        material="copper",
    )
    modeler.create_box(
        origin=[f"{x_c} + L_outer/2 - pad_wid", f"{y_c} - g_cap/2 - pad_len", z0],
        sizes=["pad_wid", "pad_len", "t_cu"],
        name=pad_b,
        material="copper",
    )

    return loop_name, pad_a, pad_b


def centers_symmetric(centers: Iterable[tuple[float, float]]) -> bool:
    rounded = {(round(x, 6), round(y, 6)) for x, y in centers}
    return all((-x, -y) in rounded for x, y in rounded)


def build_array(hfss: Hfss, params: LoopArrayParams) -> LoopBuildResult:
    modeler = cast(Modeler3D, hfss.modeler)
    modeler.model_units = "mm"
    set_design_variables(hfss, params)
    create_substrate(modeler)

    pitch_val = params.L_outer + params.g_loop
    pcb_size_val = 3 * pitch_val + params.L_outer + 2 * params.m_edge
    centers: list[tuple[float, float]] = []
    loop_names: list[str] = []
    pad_names: list[str] = []

    for i in range(4):
        for j in range(4):
            x_val = (i - 1.5) * pitch_val
            y_val = (j - 1.5) * pitch_val
            centers.append((x_val, y_val))
            loop_name, pad_a, pad_b = create_loop(modeler, i, j)
            loop_names.append(loop_name)
            pad_names.extend([pad_a, pad_b])

    return LoopBuildResult(
        pcb_size=pcb_size_val,
        loop_names=loop_names,
        pad_names=pad_names,
        centers=centers,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a 4x4 planar square loop array in HFSS using PyAEDT."
    )
    parser.add_argument(
        "--project",
        type=Path,
        default=Path(__file__).with_suffix(".aedt"),
        help="Output AEDT project path.",
    )
    parser.add_argument(
        "--graphical",
        action="store_true",
        help="Launch AEDT with the GUI enabled.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    params = LoopArrayParams()
    validate_params(params)

    project_path = args.project.expanduser().resolve()
    hfss = Hfss(
        project=str(project_path),
        design="HFSSDesign1",
        solution_type="Modal",
        non_graphical=False,
        new_desktop=True,
    )

    try:
        results = build_array(hfss, params)
        hfss.save_project()
    finally:
        hfss.release_desktop(close_projects=True, close_desktop=True)

    pcb_size_val = results.pcb_size
    loop_names = results.loop_names
    centers = results.centers

    print("Parameters (mm):")
    print(
        "  L_outer={L_outer}, w_trace={w_trace}, t_cu={t_cu}, t_sub={t_sub}, "
        "g_loop={g_loop}, m_edge={m_edge}, g_cap={g_cap}, pad_len={pad_len}, "
        "pad_wid={pad_wid}".format(**params.__dict__)
    )
    print(f"PCB size (mm): {pcb_size_val:.3f} x {pcb_size_val:.3f}")
    print(f"Loops created: {len(loop_names)}")
    print(f"Centers symmetric about origin: {centers_symmetric(centers)}")


if __name__ == "__main__":
    main()
