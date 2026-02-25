from __future__ import annotations

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput
from peetsfea.types.manifest import EmPolicy


def build_boundary(policy: EmPolicy) -> dict[str, str]:
    return {
        "type": "radiation",
        "margin_mm": str(float(policy["radiation_margin_mm"])),
    }


def build_ports(hfss: Hfss, modeler: Modeler3D, em_input: EmPipelineInput) -> dict[str, list[str]]:
    _ = (hfss, modeler)
    endpoints = em_input["endpoints"]
    tx_ports = [f"tx_port_{idx}" for idx, _ in enumerate(endpoints["tx"])]
    rx_ports = [f"rx_port_{idx}" for idx, _ in enumerate(endpoints["rx"])]
    return {"tx": tx_ports, "rx": rx_ports}
