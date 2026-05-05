from __future__ import annotations

import build123d as bd
from build123d.topology import Shape
import pytest

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
