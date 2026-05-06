from __future__ import annotations

import build123d as bd
from build123d.topology import Shape
import pytest

from peetsfea.type2_single_coil_underlay import build_tx_inner_single_coil_void_stack_shapes
from peetsfea.type2_single_coil_underlay import resolve_tx_inner_single_coil_void_stack_placement_descriptor
from peetsfea.type2_single_coil_underlay import single_coil_scene_children_with_ferrite_pet_psa_clearance


def _box_shape(
    *,
    label: str,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
) -> Shape:
    shape = bd.Box(*size_xyz, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)).moved(
        bd.Location(origin_xyz)
    )
    solids = tuple(shape.solids())
    assert len(solids) == 1
    solid = solids[0]
    solid.label = label
    return solid


def _volume(*, shape: Shape) -> float:
    return sum(solid.volume for solid in shape.solids())


def _intersection_volume(*, first: Shape, second: Shape) -> float:
    shared_shape = first.intersect(second)
    if shared_shape is None:
        return 0.0
    assert isinstance(shared_shape, Shape)
    return _volume(shape=shared_shape)


def _x_bounds(*, shape: Shape) -> tuple[float, float]:
    solids = tuple(shape.solids())
    assert len(solids) == 1
    bounding_box = solids[0].bounding_box()
    return (bounding_box.min.X, bounding_box.max.X)


def _x_bound_values(*, shapes: tuple[Shape, ...]) -> tuple[float, ...]:
    values: list[float] = []
    for shape in shapes:
        min_x, max_x = _x_bounds(shape=shape)
        values.append(min_x)
        values.append(max_x)
    return tuple(values)


def test_single_coil_clearance_cuts_fr4_blank_with_explicit_ferrite_group() -> None:
    ferrite = _box_shape(label="tx_underlay_ferrite_u0", origin_xyz=(2.0, 1.0, 0.0), size_xyz=(2.0, 3.0, 1.0))
    pet_psa = _box_shape(label="tx_underlay_pet_psa_u0", origin_xyz=(4.0, 1.0, 0.0), size_xyz=(1.0, 3.0, 1.0))
    air = _box_shape(label="tx_wall_air_u0", origin_xyz=(5.0, 1.0, 0.0), size_xyz=(1.0, 3.0, 1.0))
    ferrite_group = bd.Compound(children=(ferrite, pet_psa, air), label="g_ferrite_tx")
    fr4_blank = _box_shape(label="tx_board_fr4", origin_xyz=(0.0, 0.0, -0.5), size_xyz=(8.0, 5.0, 2.0))
    copper = _box_shape(label="tx_copper", origin_xyz=(10.0, 0.0, 0.0), size_xyz=(1.0, 1.0, 1.0))
    scene_children = (fr4_blank, ferrite_group, copper)

    cleared = single_coil_scene_children_with_ferrite_pet_psa_clearance(
        scene_children=scene_children,
        ferrite_tool_labels=(),
        ferrite_tool_group_labels=("g_ferrite_tx",),
        pcb_blank_labels=("tx_board_fr4",),
        context="test tx single-coil clearance",
    )

    assert tuple(shape.label for shape in cleared) == ("tx_board_fr4", "g_ferrite_tx", "tx_copper")
    assert cleared[1] is ferrite_group
    assert cleared[2] is copper
    assert _volume(shape=cleared[0]) == pytest.approx(_volume(shape=fr4_blank) - _volume(shape=ferrite) - _volume(shape=pet_psa))
    assert _intersection_volume(first=cleared[0], second=ferrite) == pytest.approx(0.0, abs=1e-9)
    assert _intersection_volume(first=cleared[0], second=pet_psa) == pytest.approx(0.0, abs=1e-9)
    assert _intersection_volume(first=cleared[0], second=air) > 0.0


def test_single_coil_clearance_can_derive_ferrite_pet_tools_by_label_predicate() -> None:
    fr4_blank = _box_shape(label="rx_pcb_fr4", origin_xyz=(0.0, 0.0, 0.0), size_xyz=(5.0, 5.0, 1.0))
    ferrite = _box_shape(label="under_rx_ferrite_u0", origin_xyz=(1.0, 1.0, -0.5), size_xyz=(1.0, 1.0, 2.0))
    pet_psa = _box_shape(label="under_rx_pet_psa_u0", origin_xyz=(2.0, 1.0, -0.5), size_xyz=(1.0, 1.0, 2.0))
    scene_children = (fr4_blank, ferrite, pet_psa)

    cleared = single_coil_scene_children_with_ferrite_pet_psa_clearance(
        scene_children=scene_children,
        ferrite_tool_labels=(),
        ferrite_tool_group_labels=(),
        pcb_blank_labels=("rx_pcb_fr4",),
        context="test rx single-coil clearance",
    )

    assert tuple(shape.label for shape in cleared) == ("rx_pcb_fr4", "under_rx_ferrite_u0", "under_rx_pet_psa_u0")
    assert _intersection_volume(first=cleared[0], second=ferrite) == pytest.approx(0.0, abs=1e-9)
    assert _intersection_volume(first=cleared[0], second=pet_psa) == pytest.approx(0.0, abs=1e-9)


def test_single_coil_clearance_requires_non_empty_tools_for_expected_cut() -> None:
    fr4_blank = _box_shape(label="tx_board_fr4", origin_xyz=(0.0, 0.0, 0.0), size_xyz=(5.0, 5.0, 1.0))

    with pytest.raises(RuntimeError, match=r"requires at least one ferrite/PET_PSA tool shape"):
        single_coil_scene_children_with_ferrite_pet_psa_clearance(
            scene_children=(fr4_blank,),
            ferrite_tool_labels=(),
            ferrite_tool_group_labels=(),
            pcb_blank_labels=("tx_board_fr4",),
            context="test empty tool clearance",
        )


def test_tx_inner_void_stack_uses_largest_equal_pair_count_that_fits() -> None:
    descriptor = resolve_tx_inner_single_coil_void_stack_placement_descriptor(
        void_min_x=10.0,
        void_max_x=14.8,
        void_min_y=1.0,
        void_max_y=3.0,
        z_bottom=-0.5,
        z_top=0.5,
        pet_psa_thickness_mm=0.4,
        ferrite_thickness_mm=0.6,
    )

    shapes = build_tx_inner_single_coil_void_stack_shapes(descriptor)

    assert tuple(shape.label for shape in shapes) == (
        "tx_void_ferrite_u0",
        "tx_void_pet_psa_u0",
        "tx_void_ferrite_u1",
        "tx_void_pet_psa_u1",
        "tx_void_ferrite_u2",
        "tx_void_pet_psa_u2",
        "tx_void_ferrite_u3",
        "tx_void_pet_psa_u3",
    )
    assert _x_bound_values(shapes=shapes) == pytest.approx(
        (
            10.0,
            10.7,
            10.7,
            11.2,
            11.2,
            11.9,
            11.9,
            12.4,
            12.4,
            13.1,
            13.1,
            13.6,
            13.6,
            14.3,
            14.3,
            14.8,
        )
    )


def test_tx_inner_void_stack_reduces_pair_count_when_four_pairs_do_not_fit() -> None:
    descriptor = resolve_tx_inner_single_coil_void_stack_placement_descriptor(
        void_min_x=0.0,
        void_max_x=3.9,
        void_min_y=0.0,
        void_max_y=1.0,
        z_bottom=0.0,
        z_top=1.0,
        pet_psa_thickness_mm=0.4,
        ferrite_thickness_mm=0.6,
    )

    shapes = build_tx_inner_single_coil_void_stack_shapes(descriptor)

    assert tuple(shape.label for shape in shapes) == (
        "tx_void_ferrite_u0",
        "tx_void_pet_psa_u0",
        "tx_void_ferrite_u1",
        "tx_void_pet_psa_u1",
        "tx_void_ferrite_u2",
        "tx_void_pet_psa_u2",
    )
    assert _x_bounds(shape=shapes[-1])[1] == pytest.approx(3.9)


def test_tx_inner_void_stack_fails_when_minimum_pair_does_not_fit() -> None:
    descriptor = resolve_tx_inner_single_coil_void_stack_placement_descriptor(
        void_min_x=0.0,
        void_max_x=0.9,
        void_min_y=0.0,
        void_max_y=1.0,
        z_bottom=0.0,
        z_top=1.0,
        pet_psa_thickness_mm=0.4,
        ferrite_thickness_mm=0.6,
    )

    with pytest.raises(RuntimeError, match=r"void stack width cannot fit one minimum .* pair"):
        build_tx_inner_single_coil_void_stack_shapes(descriptor)
