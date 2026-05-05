from __future__ import annotations

from typing import TypedDict

from .geometry import GroupEndpointEntry


class EmReadyObjects(TypedDict):
    tx_conductors: list[str]
    rx_conductors: list[str]
    ferrite_objects: list[str]
    fr4_objects: list[str]
    scene_bbox_source_objects: list[str]


class EmEndpoints(TypedDict):
    tx: list[GroupEndpointEntry]
    rx: list[GroupEndpointEntry]


class EmPorts(TypedDict):
    tx: list[str]
    rx: list[str]


class EmContext(TypedDict):
    dd_mirror_plane: str
    rx_plane: str
    tx_vertical_plane: str
    source: str
    object_names: list[str]


class EmPolicy(TypedDict):
    radiation_margin_mm: float
    setup_frequency_hz: float
    sweep_start_hz: float
    sweep_stop_hz: float
    validation_gate: str
    max_delta_s: float
    maximum_passes: int
    minimum_passes: int
    minimum_converged_passes: int
    percent_refinement: int
    basis_order: int
    port_accuracy: int


class OutputVariableSpec(TypedDict):
    name: str
    expression: str


class OutputsSpec(TypedDict):
    mode: str
    report_name: str
    solution_name: str
    primary_sweep: str
    report_category: str
    plot_type: str
    variables: list[OutputVariableSpec]


class PostTemplateResult(TypedDict):
    template_id: str
    report_name: str
    solution_name: str
    traces: list[str]
    output_variables: list[str]


class EmPortAssignmentEntry(TypedDict):
    boundary_name: str
    excitation_name: str
    signal_object_name: str
    signal_edge_id: int
    reference_object_name: str
    reference_edge_id: int


class EmPortAssignments(TypedDict):
    tx: list[EmPortAssignmentEntry]
    rx: list[EmPortAssignmentEntry]


class EmPipelineResult(TypedDict):
    groups: dict[str, list[str]]
    series: dict[str, list[str]]
    subtract: dict[str, list[str]]
    boundary: dict[str, str]
    ports: EmPorts
    sources: dict[str, str]
    analysis: dict[str, float | str]
    post_templates: list[PostTemplateResult]
    validation_report: dict[str, str | bool]
