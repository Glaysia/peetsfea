from __future__ import annotations

from collections.abc import Sequence
from typing import cast

import pytest

from peetsfea.aedt.protocols import ModelerSession
from peetsfea.backend.pyaedt.type2_step_import_core import _assert_imported_object_bounds_match_ledger
from peetsfea.backend.pyaedt.type2_step_import_style import _create_port_sheet_from_contract


class _RuntimeContractFakeObject:
    def __init__(
        self,
        name: str,
        *,
        bounding_box: tuple[float, float, float, float, float, float] = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0),
    ) -> None:
        self.name = name
        self.bounding_box = list(bounding_box)
        self.valid_properties = ["Color", "Transparent", "Model", "Group"]
        self._material_name = "vacuum"

    @property
    def material_name(self) -> str:
        return self._material_name

    @material_name.setter
    def material_name(self, value: str) -> None:
        self._material_name = value


class _RuntimeContractFakeModeler:
    def __init__(self) -> None:
        self.objects: dict[str, _RuntimeContractFakeObject] = {}
        self.create_polyline_calls: list[dict[str, object]] = []
        self.cover_lines_calls: list[str] = []
        self.model_state_calls: list[tuple[str, bool]] = []

    def create_polyline(self, **kwargs: object) -> object:
        self.create_polyline_calls.append(dict(kwargs))
        name = kwargs["name"]
        assert isinstance(name, str)
        obj = _RuntimeContractFakeObject(name)
        self.objects[name] = obj
        return obj

    def cover_lines(self, assignment: str) -> object:
        self.cover_lines_calls.append(assignment)
        self.objects[assignment] = _RuntimeContractFakeObject(assignment)
        return assignment

    def get_object_from_name(self, assignment: str) -> object:
        return self.objects[assignment]

    def set_object_model_state(self, name: str, model: bool) -> object:
        self.model_state_calls.append((name, model))
        return True


def _single_coil_modeled_entry(
    *,
    vertices_xyz: list[list[float]],
    canonical_min_xyz: Sequence[float] = (10.0, 20.0, 32.0),
    canonical_size_xyz: Sequence[float] = (5.0, 1.0, 1.0),
    exported_body_min_xyz: Sequence[float] = (10.0, 20.0, 30.0),
    exported_body_size_xyz: Sequence[float] = (5.0, 6.0, 7.0),
) -> dict[str, object]:
    return {
        "object_id": "tx_inner_rect_void_coil",
        "role": "tx_inner_single_coil",
        "canonical_coordinates": {
            "outer_bounds_min_xyz": list(canonical_min_xyz),
            "outer_bounds_size_xyz": list(canonical_size_xyz),
        },
        "exported_body_canonical_coordinates": {
            "outer_bounds_min_xyz": list(exported_body_min_xyz),
            "outer_bounds_size_xyz": list(exported_body_size_xyz),
        },
        "terminal_metadata": {
            "kind": "single_coil_port_v1",
            "sheet_name": "tx_inner_port_sheet",
            "vertices_xyz": vertices_xyz,
            "integration_line_start_xyz": [10.0, 20.5, 30.0],
            "integration_line_end_xyz": [15.0, 20.5, 30.0],
        },
    }


def test_create_port_sheet_from_contract_passes_ledger_vertices_to_polyline() -> None:
    vertices_xyz = [
        [10.0, 20.0, 30.0],
        [15.0, 20.0, 30.0],
        [15.0, 21.0, 30.0],
        [10.0, 21.0, 30.0],
    ]
    modeler = _RuntimeContractFakeModeler()

    names = _create_port_sheet_from_contract(
        modeler=cast(ModelerSession, modeler),
        modeled_entry=_single_coil_modeled_entry(vertices_xyz=vertices_xyz),
        context="modeled_objects[0]",
    )

    assert names == ["tx_inner_port_sheet"]
    assert modeler.create_polyline_calls == [
        {
            "points": vertices_xyz,
            "name": "tx_inner_port_sheet",
            "material": "vacuum",
            "close_surface": True,
            "cover_surface": False,
        }
    ]
    assert modeler.cover_lines_calls == ["tx_inner_port_sheet"]
    assert modeler.model_state_calls == [("tx_inner_port_sheet", True)]


def test_imported_bbox_drift_fails_before_port_sheet_creation() -> None:
    vertices_xyz = [
        [10.0, 20.0, 30.0],
        [15.0, 20.0, 30.0],
        [15.0, 21.0, 30.0],
        [10.0, 21.0, 30.0],
    ]
    modeler = _RuntimeContractFakeModeler()
    modeler.objects["tx_inner_copper_l0"] = _RuntimeContractFakeObject(
        "tx_inner_copper_l0",
        bounding_box=(10.0, 20.0, 32.0, 15.0, 26.0, 39.0),
    )
    modeled_entry = _single_coil_modeled_entry(
        vertices_xyz=vertices_xyz,
        canonical_min_xyz=[10.0, 20.0, 32.0],
        canonical_size_xyz=[5.0, 6.0, 7.0],
        exported_body_min_xyz=[10.0, 20.0, 30.0],
        exported_body_size_xyz=[5.0, 6.0, 7.0],
    )

    with pytest.raises(ValueError, match=r"imported body bbox min drift exceeds tolerance"):
        _assert_imported_object_bounds_match_ledger(
            modeler=cast(ModelerSession, modeler),
            modeled_entry=modeled_entry,
            imported_object_names=["tx_inner_copper_l0"],
            context="modeled_objects[0]",
        )

    assert modeler.create_polyline_calls == []


def test_imported_bbox_match_allows_contract_sheet_creation() -> None:
    vertices_xyz = [
        [10.0, 20.0, 30.0],
        [15.0, 20.0, 30.0],
        [15.0, 21.0, 30.0],
        [10.0, 21.0, 30.0],
    ]
    modeler = _RuntimeContractFakeModeler()
    modeler.objects["tx_inner_copper_l0"] = _RuntimeContractFakeObject(
        "tx_inner_copper_l0",
        bounding_box=(10.0, 20.0, 30.0, 15.0, 26.0, 37.0),
    )
    modeled_entry = _single_coil_modeled_entry(
        vertices_xyz=vertices_xyz,
        canonical_min_xyz=[10.0, 20.0, 32.0],
        canonical_size_xyz=[5.0, 1.0, 1.0],
        exported_body_min_xyz=[10.0, 20.0, 30.0],
        exported_body_size_xyz=[5.0, 6.0, 7.0],
    )

    _assert_imported_object_bounds_match_ledger(
        modeler=cast(ModelerSession, modeler),
        modeled_entry=modeled_entry,
        imported_object_names=["tx_inner_copper_l0"],
        context="modeled_objects[0]",
    )
    _create_port_sheet_from_contract(
        modeler=cast(ModelerSession, modeler),
        modeled_entry=modeled_entry,
        context="modeled_objects[0]",
    )

    assert modeler.create_polyline_calls[0]["points"] == vertices_xyz
