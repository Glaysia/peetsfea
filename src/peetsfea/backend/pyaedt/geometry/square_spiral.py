from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import cast

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.types.manifest import GeometryMetadata, Manifest


def _square_spiral_points(turns: int, outer: float, trace: float, gap: float) -> list[list[float]]:
    centerline_outer = outer - trace
    pitch = trace + gap
    if centerline_outer <= 0:
        raise ValueError("centerline outer width must be > 0")

    left = -centerline_outer / 2.0
    right = centerline_outer / 2.0
    top = centerline_outer / 2.0
    bottom = -centerline_outer / 2.0

    points: list[list[float]] = [[left, top, 0.0]]
    for idx in range(turns):
        points.append([right, top, 0.0])
        points.append([right, bottom, 0.0])
        points.append([left, bottom, 0.0])
        if idx == turns - 1:
            break
        left += pitch
        right -= pitch
        top -= pitch
        bottom += pitch
        if left >= right or bottom >= top:
            raise ValueError("invalid spiral dimensions for requested turns")
        points.append([left, top, 0.0])
    return points


def _create_hfss_session(manifest: Manifest, aedt_path: Path) -> Hfss:
    design_name = manifest["spec"]["design_name"]
    non_graphical = manifest["inputs"]["non_graphical"]
    return Hfss(project=str(aedt_path), design=design_name, non_graphical=non_graphical, new_desktop=True)


def _build_geometry_metadata(manifest: Manifest, aedt_path: Path, object_names: list[str]) -> GeometryMetadata:
    return {
        "design_id": manifest["design_id"],
        "toml_hash": manifest["toml_hash"],
        "peetsfea_commit": manifest["peetsfea_commit"],
        "seed": manifest["seed"],
        "selected_parameters": manifest["selected_parameters"],
        "aedt_path": str(aedt_path),
        "object_names": object_names,
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def build_square_spiral_from_manifest(manifest: Manifest) -> GeometryMetadata:
    selected = manifest["selected_parameters"]
    turns = selected["turns"]
    outer = selected["outer"]
    trace = selected["trace"]
    gap = selected["gap"]
    thickness = selected["thickness"]

    if turns < 1:
        raise ValueError("selected_parameters.turns must be >= 1")
    if trace <= 0:
        raise ValueError("selected_parameters.trace must be > 0")
    if gap < 0:
        raise ValueError("selected_parameters.gap must be >= 0")
    if thickness <= 0:
        raise ValueError("selected_parameters.thickness must be > 0")

    inner_width = outer - (2.0 * turns * trace) - (2.0 * (turns - 1) * gap)
    if inner_width <= 0:
        raise ValueError("Invalid geometry: inner width must be > 0")

    run_dir = Path(manifest["inputs"]["ansys_run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)

    design_id = manifest["design_id"]
    aedt_path = run_dir / f"{design_id}.aedt"
    points = _square_spiral_points(turns=turns, outer=outer, trace=trace, gap=gap)

    hfss = _create_hfss_session(manifest=manifest, aedt_path=aedt_path)
    modeler = cast(Modeler3D, hfss.modeler)

    close_on_exit = manifest["inputs"]["close_on_exit"]

    object_names: list[str] = []
    try:
        coil_name = f"coil1_{design_id}"
        coil_obj = modeler.create_polyline(
            points=points,
            name=coil_name,
            material="copper",
            xsection_type="Rectangle",
            xsection_width=cast(int, trace),
            xsection_height=cast(int, thickness),
        )

        obj_name = getattr(coil_obj, "name", None) or coil_name
        object_names.append(str(obj_name))

        hfss.save_project(str(aedt_path))
    except Exception as exc:
        raise RuntimeError(f"Failed to build geometry with Pyaedt: {exc}") from exc
    finally:
        try:
            hfss.release_desktop(close_projects=close_on_exit, close_desktop=close_on_exit)
        except Exception:
            pass

    metadata = _build_geometry_metadata(manifest=manifest, aedt_path=aedt_path, object_names=object_names)
    metadata_path = run_dir / f"geometry_metadata_{design_id}.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata["metadata_path"] = str(metadata_path)
    return metadata
