from __future__ import annotations

from .build_common import *
from .build_port_ops import _points_close

def _landing_edge_length(landing: _DirectedLandingSection) -> float:
    dx = landing["p_plus"][0] - landing["p_minus"][0]
    dy = landing["p_plus"][1] - landing["p_minus"][1]
    dz = landing["p_plus"][2] - landing["p_minus"][2]
    return math.sqrt((dx * dx) + (dy * dy) + (dz * dz))

def _landing_edge_as_polygon_edge(landing: _DirectedLandingSection) -> list[list[float]]:
    return [
        [landing["p_plus"][0], landing["p_plus"][1], landing["p_plus"][2]],
        [landing["p_minus"][0], landing["p_minus"][1], landing["p_minus"][2]],
    ]

def _bridge_edge_as_polygon_edge(landing: _DirectedLandingSection) -> list[list[float]]:
    assert "bridge_stub_edge" in landing, (
        "DD bridge topology contract violation: bridge_stub_edge is required before bridge sheet construction "
        f"(object_name={landing['object_name']})"
    )
    stored_edge = cast(_Edge2P, landing["bridge_stub_edge"])
    first, second = stored_edge
    if abs(first[1] - second[1]) > 1e-9 or abs(first[2] - second[2]) > 1e-9:
        raise ValueError(
            "DD bridge topology contract violation: stored bridge stub edge must be X-parallel "
            f"(object_name={landing['object_name']}, edge={stored_edge})"
        )
    if abs(first[0] - second[0]) <= 1e-9:
        raise ValueError(
            "DD bridge topology contract violation: stored bridge stub edge must have X span "
            f"(object_name={landing['object_name']}, edge={stored_edge})"
        )
    return [
        [first[0], first[1], first[2]],
        [second[0], second[1], second[2]],
    ]

def _anti_parallel_bridge_sheet_points_from_landings(
    *,
    dd_landing: _DirectedLandingSection,
    vertical_landing: _DirectedLandingSection,
) -> list[list[float]]:
    dd_trace = _landing_edge_length(dd_landing)
    vertical_trace = _landing_edge_length(vertical_landing)
    if dd_trace <= 1e-12 or vertical_trace <= 1e-12:
        raise ValueError("DD landing edge length must be > 0")
    if dd_landing["center"] == vertical_landing["center"]:
        raise ValueError("DD bridge topology contract violation: landing centers must differ")
    return [
        *_bridge_edge_as_polygon_edge(dd_landing),
        *_bridge_edge_as_polygon_edge(vertical_landing),
    ]

def _anti_parallel_bridge_sheet_points(
    *,
    dd_section: _OrderedTerminalSection,
    vertical_section: _OrderedTerminalSection,
) -> list[list[float]]:
    return [
        [dd_section["p0"][0], dd_section["p0"][1], dd_section["p0"][2]],
        [dd_section["p1"][0], dd_section["p1"][1], dd_section["p1"][2]],
        [vertical_section["p0"][0], vertical_section["p0"][1], vertical_section["p0"][2]],
        [vertical_section["p1"][0], vertical_section["p1"][1], vertical_section["p1"][2]],
    ]

def _directed_landing_from_existing_edge(
    *,
    edge: _Edge2P,
    object_name: str,
    side: Literal["left", "right", "center"],
    terminal_polarity: Literal["positive", "negative", "neutral"],
    terminal_role: Literal[
        "none",
        "feed_in",
        "feed_out",
        "inter_half_entry",
        "inter_half_exit",
        "series_entry",
        "series_exit",
    ],
) -> _DirectedLandingSection:
    return {
        "p_plus": edge[0],
        "p_minus": edge[1],
        "center": (
            (edge[0][0] + edge[1][0]) / 2.0,
            (edge[0][1] + edge[1][1]) / 2.0,
            (edge[0][2] + edge[1][2]) / 2.0,
        ),
        "outward_dir": (1.0, 0.0, 0.0),
        "plane_normal": _ZX_PLANE_NORMAL,
        "object_name": object_name,
        "dd_family": "none",
        "dd_pair_index": NO_DD_PAIR_INDEX,
        "side": side,
        "terminal_polarity": terminal_polarity,
        "terminal_role": terminal_role,
    }

def _resolve_tx_vertical_zx_chain_end_landings(
    tx_vertical_nodes_by_board: dict[_BoardKey, list[_TxVerticalLinkNode]],
) -> tuple[_DirectedLandingSection, _DirectedLandingSection]:
    flattened_nodes: list[_TxVerticalLinkNode] = []
    for nodes in tx_vertical_nodes_by_board.values():
        flattened_nodes.extend(nodes)
    if len(flattened_nodes) < 2:
        raise ValueError("tx_vertical ZX chain-end contract violation: expected at least 2 linked nodes")
    sorted_nodes = sorted(flattened_nodes, key=lambda node: (node[4], node[0], node[1]))
    lower_node = sorted_nodes[0]
    upper_node = sorted_nodes[-1]
    lower_landing = _directed_landing_from_existing_edge(
        edge=lower_node[8],
        object_name=lower_node[1],
        side="left",
        terminal_polarity="negative",
        terminal_role="series_exit",
    )
    upper_landing = _directed_landing_from_existing_edge(
        edge=upper_node[7],
        object_name=upper_node[1],
        side="right",
        terminal_polarity="positive",
        terminal_role="series_entry",
    )
    return upper_landing, lower_landing

def _resolve_tx_vertical_zx_series_chain_landings(
    tx_vertical_nodes_by_board: dict[_BoardKey, list[_TxVerticalLinkNode]],
) -> tuple[_DirectedLandingSection, _DirectedLandingSection]:
    flattened_nodes: list[_TxVerticalLinkNode] = []
    for nodes in tx_vertical_nodes_by_board.values():
        flattened_nodes.extend(nodes)
    if not flattened_nodes:
        raise ValueError("tx_vertical ZX series-chain contract violation: expected at least 1 linked node")
    sorted_nodes = sorted(flattened_nodes, key=lambda node: (node[4], node[0], node[1]))
    lower_node = sorted_nodes[0]
    upper_node = sorted_nodes[-1]
    # Legacy ZX TX must use odd-symmetry diagonal binding, not upper->upper / lower->lower.
    # The serial chain therefore enters from the lower chain end and exits from the upper chain end.
    series_entry = _directed_landing_from_existing_edge(
        edge=lower_node[8],
        object_name=lower_node[1],
        side="left",
        terminal_polarity="positive",
        terminal_role="series_entry",
    )
    series_exit = _directed_landing_from_existing_edge(
        edge=upper_node[7],
        object_name=upper_node[1],
        side="right",
        terminal_polarity="negative",
        terminal_role="series_exit",
    )
    return series_entry, series_exit

def _complete_tx_series_chain_binding(
    *,
    inputs: _TxSeriesBindingInputs,
    series_entry: _DirectedLandingSection,
    series_exit: _DirectedLandingSection,
) -> _TxSeriesChainBinding:
    feed_in = inputs.require("feed_in")
    feed_out = inputs.require("feed_out")
    inter_half_exit = inputs.require("inter_half_exit")
    inter_half_entry = inputs.require("inter_half_entry")
    resolved_series_entry = inputs.require("series_entry") if inputs.has("series_entry") else series_entry
    resolved_series_exit = inputs.require("series_exit") if inputs.has("series_exit") else series_exit
    if inputs.has("series_entry") and inputs.require("series_entry") != series_entry:
        raise ValueError(
            "tx series binding contract violation: explicit series_entry conflicts with builder-captured series_entry"
        )
    if inputs.has("series_exit") and inputs.require("series_exit") != series_exit:
        raise ValueError(
            "tx series binding contract violation: explicit series_exit conflicts with builder-captured series_exit"
        )
    binding: _TxSeriesChainBinding = {
        "feed_in": feed_in,
        "feed_out": feed_out,
        "inter_half_exit": inter_half_exit,
        "inter_half_entry": inter_half_entry,
        "series_entry": resolved_series_entry,
        "series_exit": resolved_series_exit,
    }
    expected_roles = {
        "feed_in": "feed_in",
        "feed_out": "feed_out",
        "inter_half_exit": "inter_half_exit",
        "inter_half_entry": "inter_half_entry",
        "series_entry": "series_entry",
        "series_exit": "series_exit",
    }
    for key, expected_role in expected_roles.items():
        actual_role = binding[key]["terminal_role"]
        if actual_role != expected_role:
            raise ValueError(
                "tx series binding contract violation: unexpected terminal role "
                f"(key={key}, actual={actual_role}, expected={expected_role})"
            )
    if binding["inter_half_exit"]["terminal_polarity"] == binding["series_entry"]["terminal_polarity"]:
        raise ValueError(
            "tx series binding contract violation: inter_half_exit must use cross-sign pairing with series_entry"
        )
    if binding["inter_half_entry"]["terminal_polarity"] == binding["series_exit"]["terminal_polarity"]:
        raise ValueError(
            "tx series binding contract violation: inter_half_entry must use cross-sign pairing with series_exit"
        )
    return binding

def _quantized_point(point: _Point3, *, digits: int = 9) -> _Point3:
    return (round(point[0], digits), round(point[1], digits), round(point[2], digits))

def _normalized_edge(edge: _Edge2P) -> tuple[_Point3, _Point3]:
    quantized = (_quantized_point(edge[0]), _quantized_point(edge[1]))
    return quantized if quantized[0] <= quantized[1] else (quantized[1], quantized[0])

def _normalized_polyline_segments(points: list[_Point3]) -> set[tuple[_Point3, _Point3]]:
    segments: set[tuple[_Point3, _Point3]] = set()
    for first, second in zip(points, points[1:], strict=False):
        segments.add(_normalized_edge((first, second)))
    return segments

def _assert_legacy_zx_tx_series_chain_graph(
    *,
    binding: _TxSeriesChainBinding,
    txdd_right_object_names: dict[int, str],
    group_objects: GroupObjects,
    txdd_port_owner_names_by_board: dict[str, set[str]],
) -> None:
    live_conductor_names = set(txdd_right_object_names.values()) | set(group_objects["tx_vertical"])
    if len(live_conductor_names) != 1:
        raise ValueError(
            "tx legacy ZX series graph violation: expected a single connected TX conductor "
            f"(live_conductors={sorted(live_conductor_names)})"
        )
    if binding["feed_in"]["terminal_polarity"] == binding["feed_out"]["terminal_polarity"]:
        raise ValueError("tx legacy ZX series graph violation: external feed endpoints must use opposite polarity")
    if binding["feed_in"]["terminal_role"] != "feed_in" or binding["feed_out"]["terminal_role"] != "feed_out":
        raise ValueError(
            "tx legacy ZX series graph violation: external endpoints must preserve feed terminal roles "
            f"(feed_in={binding['feed_in']['terminal_role']}, feed_out={binding['feed_out']['terminal_role']})"
        )
    for board_id, owner_names in sorted(txdd_port_owner_names_by_board.items()):
        if len(owner_names) != 1:
            raise ValueError(
                "tx legacy ZX series graph violation: board-local TX owner set must converge to one conductor "
                f"(board_id={board_id}, owners={sorted(owner_names)})"
            )

def _assert_tx_conductor_graph_common(
    *,
    txdd_right_object_names: dict[int, str],
    group_objects: GroupObjects,
    txdd_port_owner_names_by_board: dict[str, set[str]],
    txdd_start_stub_port_edges_by_board: dict[str, list[_Edge2P]],
    context: str,
) -> None:
    live_conductor_names = set(txdd_right_object_names.values()) | set(group_objects["tx_vertical"])
    if len(live_conductor_names) != 1:
        raise ValueError(
            f"{context} expected a single connected TX conductor "
            f"(live_conductors={sorted(live_conductor_names)})"
        )
    if False and txdd_start_stub_port_edges_by_board:
        total_external_edges = sum(len(port_edges) for port_edges in txdd_start_stub_port_edges_by_board.values())
        if total_external_edges != 2:
            raise ValueError(
                f"{context} expected exactly 2 external TX feed terminal edges "
                f"(actual={total_external_edges})"
            )
    for board_id, owner_names in sorted(txdd_port_owner_names_by_board.items()):
        if len(owner_names) != 1:
            raise ValueError(
                f"{context} board-local TX owner set must converge to one conductor "
                f"(board_id={board_id}, owners={sorted(owner_names)})"
            )

def _assert_stacked_tx_dd_half_conductors_closed(
    *,
    txdd_right_a_points: dict[int, tuple[_Point3, float]],
    txdd_right_object_names: dict[int, str],
) -> None:
    if {0, 1}.issubset(txdd_right_a_points):
        if set(txdd_right_object_names.keys()) != {0, 1}:
            raise ValueError(
                "stacked tx_dd right half closure violation: expected both layer object names before final interconnect "
                f"(actual_keys={sorted(txdd_right_object_names.keys())})"
            )
        if len(set(txdd_right_object_names.values())) != 1:
            raise ValueError(
                "stacked tx_dd right half closure violation: lower/upper right traces must be united before final interconnect "
                f"(objects={sorted(set(txdd_right_object_names.values()))})"
            )


__all__ = [
    '_landing_edge_length',
    '_landing_edge_as_polygon_edge',
    '_anti_parallel_bridge_sheet_points_from_landings',
    '_anti_parallel_bridge_sheet_points',
    '_directed_landing_from_existing_edge',
    '_resolve_tx_vertical_zx_chain_end_landings',
    '_resolve_tx_vertical_zx_series_chain_landings',
    '_complete_tx_series_chain_binding',
    '_quantized_point',
    '_normalized_edge',
    '_normalized_polyline_segments',
    '_assert_legacy_zx_tx_series_chain_graph',
    '_assert_tx_conductor_graph_common',
    '_assert_stacked_tx_dd_half_conductors_closed',
]
