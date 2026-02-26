from __future__ import annotations

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.types.manifest import EmPolicy


def _region_object_name(region: object) -> str:
    name = getattr(region, "name", None)
    if isinstance(name, str) and name:
        return name
    raise ValueError("create_region did not return a region object with a valid name")


def build_boundary(hfss: Hfss, modeler: Modeler3D, policy: EmPolicy) -> dict[str, str]:
    margin_mm = float(policy["radiation_margin_mm"])
    pad_value_mm = int(round(margin_mm))
    region = modeler.create_region(
        pad_value=pad_value_mm,
        pad_type="Absolute Offset",
        name=f"Region_Abs_{pad_value_mm}mm",
    )
    if not region:
        raise ValueError(f"Failed to create region with Absolute Offset margin={margin_mm}mm")
    region_name = _region_object_name(region)
    region_faces = modeler.get_object_faces(region_name)
    if len(region_faces) != 6:
        raise ValueError(
            "Created region does not expose 6 faces required for radiation assignment "
            f"(region={region_name}, face_count={len(region_faces)})"
        )
    for idx, face_id in enumerate(region_faces):
        rad_name = f"Rad_RegionAbs_{idx}"
        boundary = hfss.assign_radiation_boundary_to_faces([face_id], name=rad_name)
        if not boundary:
            raise ValueError(
                "Failed to assign radiation boundary on region face "
                f"(region={region_name}, face_id={face_id}, boundary={rad_name})"
            )
    return {
        "type": "radiation",
        "offset_type": "Absolute Offset",
        "offset_value": str(margin_mm),
        "region_name": region_name,
        "face_count": str(len(region_faces)),
    }


def build_ports(hfss: Hfss, modeler: Modeler3D, em_input: EmPipelineInput) -> dict[str, list[str]]:
    _ = (hfss, modeler)
    endpoints = em_input["endpoints"]
    tx_ports = ["TX_TML"] if endpoints["tx"] else []
    rx_ports = ["RX_TML"] if endpoints["rx"] else []
    return {"tx": tx_ports, "rx": rx_ports}
