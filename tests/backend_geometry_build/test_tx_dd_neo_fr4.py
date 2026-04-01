from __future__ import annotations

from typing import cast

import pytest
from peetsfea.aedt import Modeler3D

from peetsfea.backend.pyaedt.geometry.build_state import FinalizeInputs, GeometryBuildState, require_tx_dd_scene, set_tx_dd_scene
from peetsfea.backend.pyaedt.geometry.builders.group_builder_tx_dd_neo import build_for_board as build_tx_dd_neo_for_board
from peetsfea.backend.pyaedt.geometry.builders.group_builder_tx_dd_neo import _place_single_layer_tx_dd_path
from peetsfea.backend.pyaedt.geometry.builders.group_builder_tx_dd_neo import _resolve_single_layer_path
from peetsfea.types.manifest import GroupGeometryParams, ResolvedCoilGroup, ResolvedPcbInstance
from peetsfea.types.manifest import SelectedParameters
from tests.backend_geometry_build._one_turn_geometry_build_support import _FakeModeler, _ctx_base


def _unused_edge_points_at_path_end(**kwargs: object) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    _ = kwargs
    raise AssertionError("tx_dd neo FR4 stage must not request tx_dd copper edge points")


def _tx_dd_pcb(*, pcb_id: str, z_mm: float, selector_indices: tuple[int, ...]) -> ResolvedPcbInstance:
    mounts = [{"kind": "tx_dd", "selector_mode": "index", "selector_index": selector_index} for selector_index in selector_indices]
    return cast(
        ResolvedPcbInstance,
        {
            "id": pcb_id,
            "role": "tx",
            "position": (0.0, 0.0, z_mm),
            "rotation_deg": 0.0,
            "present": True,
            "z_mode": "absolute",
            "z_relative_base_id": None,
            "z_delta_path": None,
            "mounts": mounts,
        },
    )


def _tx_dd_group(*, layer_count: int, spacing_mm: float = 0.0) -> ResolvedCoilGroup:
    return cast(
        ResolvedCoilGroup,
        {
            "kind": "tx_dd",
            "layer_count": layer_count,
            "spacing_mm": spacing_mm,
            "instance_transforms": [{"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0}],
        },
    )


def _tx_dd_geometry(*, turn_count: int = 1) -> GroupGeometryParams:
    return cast(
        GroupGeometryParams,
        {
            "kind": "tx_dd",
            "turn_count": turn_count,
            "band_ratio": 0.2,
            "metal_ratio": 0.5,
            "trace": 1.0,
            "gap": 1.0,
        },
    )


def _selected_paths(*, right: str, left: str = "a_cw_to_A") -> SelectedParameters:
    return cast(
        SelectedParameters,
        {
            "neo_tx_dd_right_terminal_path": right,
            "neo_tx_dd_left_terminal_path": left,
        },
    )


@pytest.mark.parametrize(
    ("terminal_path", "expected_start", "expected_end", "expected_direction"),
    [
        ("D_ccw_to_d", "D", "d", "ccw"),
        ("a_cw_to_A", "a", "A", "cw"),
        ("A_ccw_to_a", "A", "a", "ccw"),
        ("A_ccw_to_d", "A", "d", "ccw"),
        ("a_cw_to_D", "a", "D", "cw"),
    ],
)
def test_tx_dd_neo_single_layer_builds_one_fr4_with_neo_identifier(
    terminal_path: str,
    expected_start: str,
    expected_end: str,
    expected_direction: str,
) -> None:
    pcb = _tx_dd_pcb(pcb_id="tx_main_0", z_mm=0.0, selector_indices=(0, 1))
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.selected = _selected_paths(right=terminal_path)
    set_tx_dd_scene(
        ctx,
        region_min=(10.0, -15.0, 0.0),
        region_max=(30.0, 15.0, 12.0),
        center_x=20.0,
        center_y=0.0,
    )
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    modeler = _FakeModeler()

    build_tx_dd_neo_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=_tx_dd_group(layer_count=1),
        geometry=_tx_dd_geometry(),
        edge_points_at_path_end=_unused_edge_points_at_path_end,
    )

    assert len(modeler.polyline_calls) == 2
    assert len(modeler.create_box_calls) == 1
    created = modeler.create_box_calls[0]
    created_name = cast(str, created["name"])
    assert created_name.startswith("neo_fr4_tx_dd_tx_main_0_l0_")
    assert "neo" in created_name
    assert cast(str, created["material"]) == "FR4_epoxy"
    assert cast(list[float], created["origin"]) == pytest.approx([10.0, -15.0, 10.265])
    assert cast(list[float], created["sizes"]) == pytest.approx([20.0, 30.0, 1.6])
    assert created_name in state.object_names
    assert state.fr4_object_names == [created_name]
    assert created_name in [probe["object_name"] for probe in state.cad_probe]
    assert modeler.objects[created_name].color == (0, 128, 0)
    assert modeler.objects[created_name].transparency == 0.85
    right_coil_name = cast(str, modeler.polyline_calls[0]["name"])
    left_coil_name = cast(str, modeler.polyline_calls[1]["name"])
    assert right_coil_name.startswith("neo_coil_tx_dd_right_tx_main_0_i1_l0_")
    assert left_coil_name.startswith("neo_coil_tx_dd_left_tx_main_0_i0_l0_")
    assert state.group_objects["tx_dd"] == [right_coil_name, left_coil_name]
    assert "tx_main_0" in finalize_inputs.txdd_start_stub_sources
    start_stub_sources = finalize_inputs.txdd_start_stub_sources["tx_main_0"]
    assert len(start_stub_sources) == 4
    assert sum(1 for source in start_stub_sources if source[2] == right_coil_name) == 2
    assert sum(1 for source in start_stub_sources if source[2] == left_coil_name) == 2
    assert finalize_inputs.tx_series_binding.has("feed_in")
    assert finalize_inputs.tx_series_binding.has("feed_out")
    assert finalize_inputs.tx_series_binding.has("inter_half_exit")
    assert finalize_inputs.tx_series_binding.has("inter_half_entry")
    assert finalize_inputs.tx_series_binding.require("feed_in")["object_name"] == right_coil_name
    assert finalize_inputs.tx_series_binding.require("inter_half_exit")["object_name"] == right_coil_name
    assert finalize_inputs.tx_series_binding.require("inter_half_entry")["object_name"] == left_coil_name
    assert finalize_inputs.tx_series_binding.require("feed_out")["object_name"] == left_coil_name
    assert state.group_endpoints[0]["start_label"] == expected_start
    assert state.group_endpoints[0]["end_label"] == expected_end
    assert state.group_endpoints[1]["start_label"] == "a"
    assert state.group_endpoints[1]["end_label"] == "A"
    assert state.coil_polarity[0]["current_direction"] == expected_direction
    assert state.coil_polarity[1]["instance_side"] == "left"
    assert modeler.objects[right_coil_name].color == (184, 115, 51)
    assert modeler.objects[right_coil_name].transparency == 0.0
    assert modeler.objects[left_coil_name].color == (184, 115, 51)
    assert modeler.objects[left_coil_name].transparency == 0.0
    right_points = cast(list[list[float]], modeler.polyline_calls[0]["points"])
    left_points = cast(list[list[float]], modeler.polyline_calls[1]["points"])
    assert min(point[0] for point in right_points) == pytest.approx(10.5)
    assert min(point[0] for point in left_points) == pytest.approx(10.5)
    assert min(point[1] for point in right_points) == pytest.approx(-max(point[1] for point in left_points))


def test_tx_dd_neo_double_layer_builds_two_fr4_boxes() -> None:
    tx_main_0 = _tx_dd_pcb(pcb_id="tx_main_0", z_mm=0.0, selector_indices=(0, 1))
    tx_main_1 = _tx_dd_pcb(pcb_id="tx_main_1", z_mm=4.0, selector_indices=(2, 3))
    ctx = _ctx_base(selected_pcbs=[tx_main_0, tx_main_1])
    ctx.selected = _selected_paths(right="D_ccw_to_d")
    set_tx_dd_scene(
        ctx,
        region_min=(10.0, -5.0, 0.0),
        region_max=(30.0, 5.0, 12.0),
        center_x=20.0,
        center_y=0.0,
    )
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    modeler = _FakeModeler()
    group = _tx_dd_group(layer_count=2)
    geometry = _tx_dd_geometry()

    build_tx_dd_neo_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=tx_main_0,
        group=group,
        geometry=geometry,
        edge_points_at_path_end=_unused_edge_points_at_path_end,
    )
    build_tx_dd_neo_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=1,
        pcb=tx_main_1,
        group=group,
        geometry=geometry,
        edge_points_at_path_end=_unused_edge_points_at_path_end,
    )

    assert modeler.polyline_calls == []
    assert [cast(str, call["name"]) for call in modeler.create_box_calls] == [
        cast(str, modeler.create_box_calls[0]["name"]),
        cast(str, modeler.create_box_calls[1]["name"]),
    ]
    assert cast(str, modeler.create_box_calls[0]["name"]).startswith("neo_fr4_tx_dd_tx_main_0_l0_")
    assert cast(str, modeler.create_box_calls[1]["name"]).startswith("neo_fr4_tx_dd_tx_main_1_l1_")
    assert cast(list[float], modeler.create_box_calls[0]["origin"]) == pytest.approx([10.0, -5.0, 10.265])
    assert cast(list[float], modeler.create_box_calls[1]["origin"]) == pytest.approx([10.0, -5.0, 6.265])
    assert cast(list[float], modeler.create_box_calls[0]["sizes"]) == pytest.approx([20.0, 10.0, 1.6])
    assert cast(list[float], modeler.create_box_calls[1]["sizes"]) == pytest.approx([20.0, 10.0, 1.6])
    assert len(state.fr4_object_names) == 2
    assert all("neo" in name for name in state.fr4_object_names)
    assert modeler.objects[state.fr4_object_names[0]].color == (0, 128, 0)
    assert modeler.objects[state.fr4_object_names[1]].color == (0, 128, 0)
    assert modeler.objects[state.fr4_object_names[0]].transparency == 0.85
    assert modeler.objects[state.fr4_object_names[1]].transparency == 0.85


def test_tx_dd_neo_single_layer_a_cw_to_A_supports_multi_turn_without_self_crossing() -> None:
    pcb = _tx_dd_pcb(pcb_id="tx_main_0", z_mm=0.0, selector_indices=(0, 1))
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.selected = _selected_paths(right="a_cw_to_A")
    ctx.tx_dd_outer_x = 100.0
    ctx.tx_dd_outer_y = 60.0
    set_tx_dd_scene(
        ctx,
        region_min=(10.0, -70.0, 0.0),
        region_max=(150.0, 70.0, 12.0),
        center_x=80.0,
        center_y=0.0,
    )
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    modeler = _FakeModeler()

    build_tx_dd_neo_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=_tx_dd_group(layer_count=1),
        geometry=_tx_dd_geometry(turn_count=3),
        edge_points_at_path_end=_unused_edge_points_at_path_end,
    )

    assert len(modeler.polyline_calls) == 2
    assert state.group_endpoints[0]["start_label"] == "a"
    assert state.group_endpoints[0]["end_label"] == "A"
    assert state.coil_polarity[0]["current_direction"] == "cw"
    right_points = cast(list[list[float]], modeler.polyline_calls[0]["points"])
    left_points = cast(list[list[float]], modeler.polyline_calls[1]["points"])
    assert min(point[1] for point in right_points) == pytest.approx(-max(point[1] for point in left_points))


def test_tx_dd_neo_single_layer_places_inner_edges_symmetrically_about_y_axis() -> None:
    pcb = _tx_dd_pcb(pcb_id="tx_main_0", z_mm=0.0, selector_indices=(0, 1))
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.selected = _selected_paths(right="D_ccw_to_d")
    set_tx_dd_scene(
        ctx,
        region_min=(10.0, -20.0, 0.0),
        region_max=(30.0, 20.0, 12.0),
        center_x=20.0,
        center_y=0.0,
    )
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    modeler = _FakeModeler()

    build_tx_dd_neo_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=_tx_dd_group(layer_count=1, spacing_mm=2.0),
        geometry=_tx_dd_geometry(),
        edge_points_at_path_end=_unused_edge_points_at_path_end,
    )

    right_points = cast(list[list[float]], modeler.polyline_calls[0]["points"])
    left_points = cast(list[list[float]], modeler.polyline_calls[1]["points"])
    assert min(point[1] for point in right_points) == pytest.approx(1.5)
    assert max(point[1] for point in left_points) == pytest.approx(-1.5)


def test_tx_dd_neo_single_layer_respects_requested_edge_gap_when_spacing_is_less_than_trace() -> None:
    pcb = _tx_dd_pcb(pcb_id="tx_main_0", z_mm=0.0, selector_indices=(0, 1))
    ctx = _ctx_base(selected_pcbs=[pcb])
    ctx.selected = _selected_paths(right="D_ccw_to_d")
    set_tx_dd_scene(
        ctx,
        region_min=(10.0, -20.0, 0.0),
        region_max=(30.0, 20.0, 12.0),
        center_x=20.0,
        center_y=0.0,
    )
    state = GeometryBuildState()
    finalize_inputs = FinalizeInputs()
    modeler = _FakeModeler()

    build_tx_dd_neo_for_board(
        modeler=cast(Modeler3D, modeler),
        ctx=ctx,
        state=state,
        finalize_inputs=finalize_inputs,
        board_idx=0,
        pcb=pcb,
        group=_tx_dd_group(layer_count=1, spacing_mm=0.25),
        geometry=_tx_dd_geometry(),
        edge_points_at_path_end=_unused_edge_points_at_path_end,
    )

    trace_width = 1.0
    right_points = cast(list[list[float]], modeler.polyline_calls[0]["points"])
    left_points = cast(list[list[float]], modeler.polyline_calls[1]["points"])
    right_inner_edge_y = min(point[1] for point in right_points) - (trace_width / 2.0)
    left_inner_edge_y = max(point[1] for point in left_points) + (trace_width / 2.0)

    assert right_inner_edge_y - left_inner_edge_y == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("terminal_path", "expected_points"),
    [
        (
            "D_ccw_to_d",
            [
                [-7.5, -4.5, 0.0],
                [9.5, -4.5, 0.0],
                [9.5, 2.5, 0.0],
                [7.5, 2.5, 0.0],
                [-7.5, 2.5, 0.0],
                [-7.5, -2.5, 0.0],
            ],
        ),
        (
            "A_ccw_to_a",
            [
                [-9.5, 2.5, 0.0],
                [-9.5, -4.5, 0.0],
                [7.5, -4.5, 0.0],
                [7.5, -2.5, 0.0],
                [7.5, 2.5, 0.0],
                [-7.5, 2.5, 0.0],
            ],
        ),
        (
            "a_cw_to_A",
            [
                [-7.5, 2.5, 0.0],
                [7.5, 2.5, 0.0],
                [7.5, -2.5, 0.0],
                [7.5, -4.5, 0.0],
                [-9.5, -4.5, 0.0],
                [-9.5, 2.5, 0.0],
            ],
        ),
    ],
)
def test_tx_dd_neo_same_corner_terminal_paths_avoid_self_touching_geometry(
    terminal_path: str,
    expected_points: list[list[float]],
) -> None:
    points, start_label, end_label, _direction = _resolve_single_layer_path(
        selected_path=terminal_path,
        turns=1,
        outer_x=20.0,
        outer_y=10.0,
        trace=1.0,
        gap=1.0,
    )

    assert start_label.upper() == end_label.upper()
    actual_points = [[point[0], point[1], point[2]] for point in points]
    assert len(actual_points) == len(expected_points)
    for actual_point, expected_point in zip(actual_points, expected_points, strict=True):
        assert actual_point == pytest.approx(expected_point)
    assert len(points) == len({(point[0], point[1], point[2]) for point in points})


def test_tx_dd_neo_same_corner_turn_count_matches_requested_turns() -> None:
    one_turn_points, _start_label, _end_label, _direction = _resolve_single_layer_path(
        selected_path="D_ccw_to_d",
        turns=1,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
    )
    two_turn_points, _start_label, _end_label, _direction = _resolve_single_layer_path(
        selected_path="D_ccw_to_d",
        turns=2,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
    )
    three_turn_points, _start_label, _end_label, _direction = _resolve_single_layer_path(
        selected_path="D_ccw_to_d",
        turns=3,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
    )

    assert len(one_turn_points) < len(two_turn_points) < len(three_turn_points)
    assert one_turn_points[-1] == pytest.approx((-17.5, -12.5, 0.0))
    assert two_turn_points[-1] == pytest.approx((-15.5, -10.5, 0.0))
    assert three_turn_points[-1] == pytest.approx((-13.5, -8.5, 0.0))


def test_tx_dd_neo_non_same_corner_completes_all_requested_turns_before_target() -> None:
    one_turn_points, _start_label, _end_label, _direction = _resolve_single_layer_path(
        selected_path="D_ccw_to_b",
        turns=1,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
    )
    two_turn_points, _start_label, _end_label, _direction = _resolve_single_layer_path(
        selected_path="D_ccw_to_b",
        turns=2,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
    )
    three_turn_points, _start_label, _end_label, _direction = _resolve_single_layer_path(
        selected_path="D_ccw_to_b",
        turns=3,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
    )

    assert len(one_turn_points) < len(two_turn_points) < len(three_turn_points)
    assert one_turn_points[-1] == pytest.approx((17.5, 12.5, 0.0))
    assert two_turn_points[-1] == pytest.approx((15.5, 10.5, 0.0))
    assert three_turn_points[-1] == pytest.approx((13.5, 8.5, 0.0))


def test_tx_dd_neo_corner_mode_applies_blunted_corners_without_toml_changes() -> None:
    sharp_points, _start_label, _end_label, sharp_direction = _resolve_single_layer_path(
        selected_path="D_ccw_to_d",
        turns=1,
        outer_x=20.0,
        outer_y=10.0,
        trace=1.0,
        gap=1.0,
        corner_mode=0,
    )
    blunted_points, _start_label, _end_label, blunted_direction = _resolve_single_layer_path(
        selected_path="D_ccw_to_d",
        turns=1,
        outer_x=20.0,
        outer_y=10.0,
        trace=1.0,
        gap=1.0,
        corner_mode=1,
    )

    assert sharp_direction == "ccw"
    assert blunted_direction == "ccw"
    assert len(blunted_points) > len(sharp_points)
    assert [9.5, -4.5, 0.0] not in [[point[0], point[1], point[2]] for point in blunted_points]


@pytest.mark.parametrize(
    ("terminal_path", "turns", "expected_start", "expected_end"),
    [
        ("D_ccw_to_d", 3, (-17.5, -14.5, 0.0), (-13.5, -8.5, 0.0)),
        ("a_cw_to_A", 3, (-13.5, 8.5, 0.0), (-19.5, 12.5, 0.0)),
    ],
)
def test_tx_dd_neo_terminal_seed_uses_next_ring_coordinates_for_outer_terminals(
    terminal_path: str,
    turns: int,
    expected_start: tuple[float, float, float],
    expected_end: tuple[float, float, float],
) -> None:
    sharp_points, _start_label, _end_label, _sharp_direction = _resolve_single_layer_path(
        selected_path=terminal_path,
        turns=turns,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
        corner_mode=0,
    )
    blunted_points, _start_label, _end_label, _blunted_direction = _resolve_single_layer_path(
        selected_path=terminal_path,
        turns=turns,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
        corner_mode=1,
    )

    assert sharp_points[0] == pytest.approx(expected_start)
    assert sharp_points[-1] == pytest.approx(expected_end)
    assert blunted_points[0] == pytest.approx(expected_start)
    assert blunted_points[-1] == pytest.approx(expected_end)


def test_tx_dd_neo_terminal_seed_leaves_non_outer_terminal_paths_unchanged() -> None:
    sharp_points, _start_label, _end_label, _sharp_direction = _resolve_single_layer_path(
        selected_path="A_ccw_to_d",
        turns=3,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
        corner_mode=0,
    )
    blunted_points, _start_label, _end_label, _blunted_direction = _resolve_single_layer_path(
        selected_path="A_ccw_to_d",
        turns=3,
        outer_x=40.0,
        outer_y=30.0,
        trace=1.0,
        gap=1.0,
        corner_mode=1,
    )

    assert sharp_points[0] == pytest.approx((-19.5, 12.5, 0.0))
    assert sharp_points[-1] == pytest.approx((-13.5, -8.5, 0.0))
    assert blunted_points[0] == pytest.approx((-19.5, 12.5, 0.0))
    assert blunted_points[-1] == pytest.approx((-13.5, -8.5, 0.0))


def test_tx_dd_neo_path_placement_helper_matches_existing_right_world_placement() -> None:
    pcb = _tx_dd_pcb(pcb_id="tx_main_0", z_mm=0.0, selector_indices=(0, 1))
    ctx = _ctx_base(selected_pcbs=[pcb])
    set_tx_dd_scene(
        ctx,
        region_min=(10.0, -5.0, 0.0),
        region_max=(30.0, 5.0, 12.0),
        center_x=20.0,
        center_y=0.0,
    )
    local_points, _start_label, _end_label, _direction = _resolve_single_layer_path(
        selected_path="D_ccw_to_d",
        turns=1,
        outer_x=20.0,
        outer_y=10.0,
        trace=1.0,
        gap=1.0,
    )

    world_points, center_y, anchor_z = _place_single_layer_tx_dd_path(
        local_points=local_points,
        tx_dd_scene=require_tx_dd_scene(ctx),
        transform={"dx": 0.0, "dy": 0.0, "dz": 0.0, "rot_deg": 0.0},
        board_z=pcb["position"][2],
        tx_dd_top_clearance=ctx.tx_dd_top_clearance,
        cu_thickness=ctx.cu_thickness,
    )

    assert center_y == pytest.approx(2.5)
    assert anchor_z == pytest.approx(11.865)
    expected_world_points = [
        [10.5, -2.0, 11.865],
        [29.5, -2.0, 11.865],
        [29.5, 5.0, 11.865],
        [27.5, 5.0, 11.865],
        [12.5, 5.0, 11.865],
        [12.5, 0.0, 11.865],
    ]
    actual_world_points = [[point[0], point[1], point[2]] for point in world_points]
    assert len(actual_world_points) == len(expected_world_points)
    for actual_point, expected_point in zip(actual_world_points, expected_world_points, strict=True):
        assert actual_point == pytest.approx(expected_point)
