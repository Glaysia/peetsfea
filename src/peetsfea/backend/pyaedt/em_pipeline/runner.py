from __future__ import annotations

from ansys.aedt.core import Hfss
from ansys.aedt.core.modeler.modeler_3d import Modeler3D

from peetsfea.backend.pyaedt.em_pipeline.analysis import build_analysis, build_post_templates
from peetsfea.backend.pyaedt.em_pipeline.boundary_port import build_boundary, build_ports
from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput, EmPipelineResult
from peetsfea.backend.pyaedt.em_pipeline.grouping import build_groups
from peetsfea.backend.pyaedt.em_pipeline.series import build_series
from peetsfea.backend.pyaedt.em_pipeline.sources import apply_sources_phase
from peetsfea.backend.pyaedt.em_pipeline.subtract import build_subtract
from peetsfea.backend.pyaedt.em_pipeline.validate import validate_pipeline
from peetsfea.types.manifest import EmPolicy, OutputsSpec


def run_em_pipeline(
    hfss: Hfss,
    modeler: Modeler3D,
    em_input: EmPipelineInput,
    em_policy: EmPolicy,
    outputs: OutputsSpec,
) -> EmPipelineResult:
    groups = build_groups(em_input)
    series = build_series(groups)
    subtract = build_subtract(groups)
    boundary = build_boundary(hfss, modeler, em_policy)
    ports = build_ports(hfss, modeler, em_input)
    sources = apply_sources_phase(hfss, ports)
    analysis = build_analysis(hfss, em_policy)
    post_templates = build_post_templates(hfss, outputs)
    result: EmPipelineResult = {
        "groups": groups,
        "series": series,
        "subtract": subtract,
        "boundary": boundary,
        "ports": ports,
        "sources": sources,
        "analysis": analysis,
        "post_templates": post_templates,
        "validation_report": {"ok": False, "gate": "pending", "message": "pending"},
    }
    result["validation_report"] = validate_pipeline(result, em_policy)
    return result
