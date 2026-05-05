from __future__ import annotations

from peetsfea.aedt import Hfss
from peetsfea.aedt import Modeler3D
from peetsfea.aedt.protocols import HfssSession
from peetsfea.aedt.protocols import ModelerSession

from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.types.manifest import EmPolicy, EmPorts


def _region_object_name(region: object) -> str:
    assert hasattr(region, "name"), "create_region did not return a region object with a name"
    name = getattr(region, "name")
    assert isinstance(name, str) and name, "create_region returned a region object without a valid name"
    return name


def build_boundary(hfss: HfssSession, modeler: ModelerSession, policy: EmPolicy) -> dict[str, str]:
    margin_mm = float(policy["radiation_margin_mm"])
    pad_value_mm = int(round(margin_mm))
    region = raise_on_false(
        modeler.create_region(
            pad_value=pad_value_mm,
            pad_type="Absolute Offset",
            name=f"Region_Abs_{pad_value_mm}mm",
        ),
        operation="create_region",
        context={"pad_value_mm": pad_value_mm},
    )
    region_name = _region_object_name(region)
    region_faces = raise_on_false(
        modeler.get_object_faces(region_name),
        operation="get_object_faces",
        context={"region": region_name},
    )
    if len(region_faces) != 6:
        raise ValueError(
            "Created region does not expose 6 faces required for radiation assignment "
            f"(region={region_name}, face_count={len(region_faces)})"
        )
    for idx, face_id in enumerate(region_faces):
        rad_name = f"Rad_RegionAbs_{idx}"
        raise_on_false(
            hfss.assign_radiation_boundary_to_faces([face_id], name=rad_name),
            operation="assign_radiation_boundary_to_faces",
            context={"region": region_name, "face_id": face_id, "boundary": rad_name},
        )
    return {
        "type": "radiation",
        "offset_type": "Absolute Offset",
        "offset_value": str(margin_mm),
        "region_name": region_name,
        "face_count": str(len(region_faces)),
    }


def build_ports(hfss: HfssSession, modeler: ModelerSession, em_input: EmPipelineInput) -> EmPorts:
    _ = (hfss, modeler)
    resolved_ports = em_input["ports"]
    tx_ports = list(resolved_ports["tx"])
    rx_ports = list(resolved_ports["rx"])
    if len(tx_ports) != 1 or len(rx_ports) != 1:
        raise ValueError(
            "EM input must provide exactly one explicit TX port and one explicit RX port "
            f"(tx_ports={tx_ports}, rx_ports={rx_ports})"
        )
    return {"tx": tx_ports, "rx": rx_ports}
