from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_import_pipeline import import_type2_step_ledger
from peetsfea.backend.pyaedt.type2_step_import_pipeline import import_type2_step_ledger_into_hfss
from peetsfea.type2_plate_stack import expected_plate_stack_body_names
from peetsfea.type2_step_ledger import ExportedBodyGroup
from tests.fixtures.legacy.type1_spec import type1_outputs_spec

_PLATE_STACK_TURN_COUNT = 3
_PLATE_STACK_STUB_LENGTH_MM = 5.0
_PLATE_STACK_PCB_TOTAL_THICKNESS_MM = 0.4
_TX_COPPER_GROUP_NAME = "g_copper_tx"
_RX_COPPER_GROUP_NAME = "g_copper_rx"
_TX_FERRITE_GROUP_NAME = "g_ferrite_tx"
_RX_FERRITE_GROUP_NAME = "g_ferrite_rx"
_TX_PLATE_COPPER_NAME = "tx_plate_copper"
_RX_PLATE_COPPER_NAME = "rx_plate_copper"
_TX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES: tuple[str, ...] = (
    "tx_underlay_ferrite_u",
    "tx_underlay_pet_psa_u",
    "tx_underlay_air_u",
    "tx_wall_ferrite_u",
    "tx_wall_pet_psa_u",
    "tx_wall_air_u",
)
_RX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES: tuple[str, ...] = (
    "under_rx_ferrite_u",
    "under_rx_pet_psa_u",
    "under_rx_air_u",
)
_TX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES: tuple[str, ...] = (
    "tx_stack_pet_psa",
    "tx_stack_ferrite",
    "tx_stack_air",
)
_RX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES: tuple[str, ...] = (
    "rx_stack_pet_psa",
    "rx_stack_ferrite",
    "rx_stack_air",
)


def _write_step(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("ISO-10303-21;\nEND-ISO-10303-21;\n", encoding="utf-8")
    return path


def _non_model_member_entry(
    *,
    object_id: str,
    role: str,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
    plane: str,
) -> dict[str, object]:
    origin_x, origin_y, origin_z = origin_xyz
    size_x, size_y, size_z = size_xyz
    return {
        "object_id": object_id,
        "role": role,
        "material": "vacuum",
        "model_state": False,
        "canonical_coordinates": {
            "frame_origin_xyz": list(origin_xyz),
            "outer_bounds_min_xyz": list(origin_xyz),
            "outer_bounds_max_xyz": [origin_x + size_x, origin_y + size_y, origin_z + size_z],
            "outer_bounds_size_xyz": list(size_xyz),
        },
        "plane": plane,
        "non_model": True,
    }


def _tx_region_actual_member_names(*, x_division_count: int = 1, y_division_count: int = 1) -> tuple[str, ...]:
    if x_division_count == 1 and y_division_count == 1:
        return ("tx_region_actual",)
    return tuple(
        f"tx_region_actual_x{x_index}_y{y_index}"
        for x_index in range(x_division_count)
        for y_index in range(y_division_count)
    )


def _tx_region_actual_member_entries(*, x_division_count: int = 1, y_division_count: int = 1) -> list[dict[str, object]]:
    tile_names = _tx_region_actual_member_names(x_division_count=x_division_count, y_division_count=y_division_count)
    tx_origin_x = 0.0
    tx_origin_y = -140.0
    tx_origin_z = 0.0
    tx_size_x = 160.0
    tx_size_y = 280.0
    tx_size_z = 90.0
    tile_size_x = tx_size_x / float(x_division_count)
    tile_size_y = tx_size_y / float(y_division_count)
    entries: list[dict[str, object]] = []
    for x_index in range(x_division_count):
        for y_index in range(y_division_count):
            tile_name = tile_names[(x_index * y_division_count) + y_index]
            entries.append(
                _non_model_member_entry(
                    object_id=tile_name,
                    role="tx_region_actual",
                    origin_xyz=(
                        tx_origin_x + (tile_size_x * float(x_index)),
                        tx_origin_y + (tile_size_y * float(y_index)),
                        tx_origin_z,
                    ),
                    size_xyz=(tile_size_x, tile_size_y, tx_size_z),
                    plane="YZ",
                )
            )
    return entries


def _non_model_entry(
    *,
    object_id: str = "type2_non_model_scene",
    tx_region_actual_x_division_count: int = 1,
    tx_region_actual_y_division_count: int = 1,
) -> dict[str, object]:
    tx_region_actual_member_names = _tx_region_actual_member_names(
        x_division_count=tx_region_actual_x_division_count,
        y_division_count=tx_region_actual_y_division_count,
    )
    return {
        "object_id": object_id,
        "role": "non_model_scene",
        "material": "vacuum",
        "model_state": False,
        "canonical_coordinates": {
            "frame_origin_xyz": [0.0, -1000.0, -461.0],
            "outer_bounds_min_xyz": [0.0, -1000.0, -461.0],
            "outer_bounds_max_xyz": [2000.0, 1000.0, 1194.0],
            "outer_bounds_size_xyz": [2000.0, 2000.0, 1655.0],
        },
        "plane": "mixed",
        "non_model": True,
        "member_object_ids": ("environment", "tx_region", *tx_region_actual_member_names, "rx_region_max"),
        "member_objects": [
            _non_model_member_entry(
                object_id="environment",
                role="environment",
                origin_xyz=(0.0, -1000.0, -461.0),
                size_xyz=(2000.0, 2000.0, 1655.0),
                plane="mixed",
            ),
            _non_model_member_entry(
                object_id="tx_region",
                role="tx_region",
                origin_xyz=(0.0, -140.0, 0.0),
                size_xyz=(160.0, 280.0, 90.0),
                plane="YZ",
            ),
            *_tx_region_actual_member_entries(
                x_division_count=tx_region_actual_x_division_count,
                y_division_count=tx_region_actual_y_division_count,
            ),
            _non_model_member_entry(
                object_id="rx_region_max",
                role="rx_region_max",
                origin_xyz=(0.0, -280.0, 139.0),
                size_xyz=(4.5, 560.0, 360.0),
                plane="YZ",
            ),
        ],
    }


def _plate_stack_non_model_entry() -> dict[str, object]:
    import copy

    return copy.deepcopy(_non_model_entry())


def _modeled_entry(
    *,
    object_id: str = "tx_rect_void_coil",
    role: str = "tx_single_coil",
    plane: str = "XY",
    placement_owner_id: str = "tx_region",
    origin_xyz: tuple[float, float, float] = (0.0, -15.0, 87.2),
    size_xyz: tuple[float, float, float] = (50.0, 30.0, 2.8),
    source_metadata_path: str = "/tmp/type2.metadata.json",
    expected_names: list[str] | None = None,
    expected_groups: list[ExportedBodyGroup] | None = None,
    pcb_layer_positions_mm: list[float] | None = None,
    copper_layer_positions_mm: list[float] | None = None,
) -> dict[str, object]:
    origin_x, origin_y, origin_z = origin_xyz
    size_x, size_y, size_z = size_xyz
    offset_x = origin_x - (-25.0)
    offset_y = origin_y - (-15.0)
    if expected_names is None:
        expected_names = (
            ["tx_pcb_l0", "tx_copper_l0"]
            if role == "tx_single_coil"
            else ["rx_pcb_l0", "rx_copper_l0"]
        )
    if pcb_layer_positions_mm is None:
        pcb_layer_positions_mm = [origin_z]
    if copper_layer_positions_mm is None:
        copper_layer_positions_mm = [origin_z + 0.4]
    if expected_groups is None:
        expected_groups = []
    if plane == "XY":
        port_sheet_vertices_xyz = [
            [origin_x, origin_y, origin_z],
            [origin_x + 5.0, origin_y, origin_z],
            [origin_x + 5.0, origin_y + 5.0, origin_z],
            [origin_x, origin_y + 5.0, origin_z],
        ]
    else:
        port_sheet_vertices_xyz = [
            [origin_x, origin_y, origin_z],
            [origin_x, origin_y + 5.0, origin_z],
            [origin_x, origin_y + 5.0, origin_z + 5.0],
            [origin_x, origin_y, origin_z + 5.0],
        ]
    return {
        "object_id": object_id,
        "role": role,
        "plane": plane,
        "placement_owner_id": placement_owner_id,
        "material": "composite",
        "model_state": True,
        "expected_exported_body_names": expected_names,
        "expected_exported_body_count": len(expected_names),
        "expected_exported_body_groups": expected_groups,
        "canonical_coordinates": {
            "frame_origin_xyz": [offset_x, offset_y, origin_z],
            "outer_bounds_min_xyz": [origin_x, origin_y, origin_z],
            "outer_bounds_max_xyz": [origin_x + size_x, origin_y + size_y, origin_z + size_z],
            "outer_bounds_size_xyz": [size_x, size_y, size_z],
            "pcb_layer_z_positions_mm": pcb_layer_positions_mm,
            "copper_layer_z_positions_mm": copper_layer_positions_mm,
        },
        "terminal_metadata": {
            "path": "A_cw_to_a",
            "outer_corner": "A",
            "inner_corner": "a",
            "direction": "cw",
            "start_point_plane_mm": [55.0, 15.0],
            "end_point_plane_mm": [70.0, 5.0],
            "port_sheet_vertices_xyz": port_sheet_vertices_xyz,
        },
        "source_metadata_path": source_metadata_path,
    }


def _tx_rect_void_columns_terminal_metadata_for_import() -> dict[str, object]:
    return {
        "kind": "parallel_collector_tabs",
        "tab_face_vertices_xyz": [
            {
                "terminal": "start",
                "vertices_xyz": [
                    [12.0, 5.0, 70.0],
                    [13.0, 5.0, 70.0],
                    [13.0, 6.0, 70.0],
                    [12.0, 6.0, 70.0],
                ],
            },
            {
                "terminal": "end",
                "vertices_xyz": [
                    [20.0, 5.0, 69.0],
                    [21.0, 5.0, 69.0],
                    [21.0, 6.0, 69.0],
                    [20.0, 6.0, 69.0],
                ],
            },
        ],
    }


def _tx_rect_void_columns_entry_for_import(tmp_path: Path) -> dict[str, object]:
    modeled_object = _modeled_entry(
        object_id="tx_rect_void_columns",
        role="tx_rect_void_columns",
        plane="XY",
        placement_owner_id="tx_region_actual_stack_space",
        origin_xyz=(10.0, -10.0, 65.0),
        size_xyz=(20.0, 20.0, 25.0),
        source_metadata_path=str(tmp_path / "tx_rect_void_columns.metadata.json"),
        expected_names=["txrvc_x0_y0_pcb_l0", "tx_rect_void_columns_copper"],
        expected_groups=[],
    )
    modeled_object["terminal_metadata"] = _tx_rect_void_columns_terminal_metadata_for_import()
    return modeled_object


def _tx_rect_void_columns_non_model_entry_for_import() -> dict[str, object]:
    non_model_object = _non_model_entry()
    stack_space_member = {
        "object_id": "tx_region_actual_stack_space",
        "role": "tx_region_actual_stack_space",
        "material": "vacuum",
        "model_state": False,
        "non_model": True,
        "plane": "XY",
        "canonical_coordinates": {
            "frame_origin_xyz": [0.0, -20.0, 60.0],
            "outer_bounds_min_xyz": [0.0, -20.0, 60.0],
            "outer_bounds_max_xyz": [40.0, 20.0, 95.0],
            "outer_bounds_size_xyz": [40.0, 40.0, 35.0],
        },
    }
    member_object_ids = list(cast(tuple[str, ...], non_model_object["member_object_ids"]))
    member_object_ids.append("tx_region_actual_stack_space")
    non_model_object["member_object_ids"] = tuple(member_object_ids)
    member_objects = list(cast(list[dict[str, object]], non_model_object["member_objects"]))
    member_objects.append(stack_space_member)
    non_model_object["member_objects"] = member_objects
    return non_model_object


def _tx_rect_void_columns_imported_name_batch_for_import() -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        "tx_region_actual_stack_space",
        "txrvc_x0_y0_pcb_l0",
        "tx_rect_void_columns_copper",
    )


def _write_ledger(
    path: Path,
    *,
    scene_step_path: Path,
    non_model_objects: list[dict[str, object]],
    modeled_objects: list[dict[str, object]],
    radiation_margin_mm: float = 3500.0,
) -> Path:
    payload = {
        "source_toml_path": str(path.parent / "type2_fixed.toml"),
        "output_dir": str(path.parent),
        "scene_step_path": str(scene_step_path),
        "seed": 7,
        "em_policy": {"radiation_margin_mm": radiation_margin_mm},
        "outputs": type1_outputs_spec(),
        "non_model_objects": non_model_objects,
        "modeled_objects": modeled_objects,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class _FakeObject:
    def __init__(self, name: str, *, valid_properties: tuple[str, ...] = ("Material", "Color", "Transparent")) -> None:
        self.name = name
        self.color = (0, 0, 0)
        self.transparency = 0.0
        self.valid_properties = list(valid_properties)
        self._material_name = "vacuum"
        self._surface_material_name = "vacuum"

    @property
    def material_name(self) -> str:
        if "Material" not in self.valid_properties:
            return ""
        return self._material_name

    @material_name.setter
    def material_name(self, material_name: str) -> None:
        if "Material" not in self.valid_properties:
            raise AttributeError("Property 'Material' does not exist.")
        self._material_name = material_name

    @property
    def surface_material_name(self) -> str:
        if "Surface Material" not in self.valid_properties:
            return ""
        return self._surface_material_name

    @surface_material_name.setter
    def surface_material_name(self, material_name: str) -> None:
        if "Surface Material" not in self.valid_properties:
            raise AttributeError("Property 'Surface Material' does not exist.")
        self._surface_material_name = material_name


def _new_fake_sheet_object(name: str) -> _FakeObject:
    return _FakeObject(name, valid_properties=("Color", "Transparent", "Model", "Group"))


class _FakeMaterial:
    def __init__(self, name: str) -> None:
        self.name = name
        self.permittivity = ""
        self.permeability = ""
        self.conductivity = ""
        self.dielectric_loss_tangent = ""
        self.magnetic_loss_tangent = ""


class _FakeMaterials:
    def __init__(self) -> None:
        self.material_keys: dict[str, _FakeMaterial] = {}
        self._pending_material_keys: dict[str, _FakeMaterial] = {}
        self.delayed_lookup_material_names: set[str] = set()
        self.aedmattolibrary_calls: list[str] = []

    def exists_material(self, name: str) -> bool:
        normalized_name = name.casefold()
        return normalized_name in self.material_keys or normalized_name in self._pending_material_keys

    def add_material(self, name: str) -> _FakeMaterial:
        material = _FakeMaterial(name)
        normalized_name = name.casefold()
        if normalized_name in {delayed.casefold() for delayed in self.delayed_lookup_material_names}:
            self._pending_material_keys[normalized_name] = material
        else:
            self.material_keys[normalized_name] = material
        return material

    def _aedmattolibrary(self, name: str) -> _FakeMaterial:
        self.aedmattolibrary_calls.append(name)
        normalized_name = name.casefold()
        if normalized_name in self._pending_material_keys:
            self.material_keys[normalized_name] = self._pending_material_keys.pop(normalized_name)
        return self.material_keys[normalized_name]


class _FakeDefinitionManager:
    def __init__(self, *, materials: _FakeMaterials) -> None:
        self.materials = materials
        self.add_material_calls: list[list[object]] = []
        self.edit_material_calls: list[tuple[str, list[object]]] = []

    def GetProjectMaterialNames(self) -> list[str]:
        return [material.name for material in self.materials.material_keys.values()]

    def AddMaterial(self, payload: list[object]) -> None:
        self.add_material_calls.append(list(payload))
        self._apply_material_payload(payload)

    def EditMaterial(self, name: str, payload: list[object]) -> None:
        self.edit_material_calls.append((name, list(payload)))
        self._apply_material_payload(payload)

    def _apply_material_payload(self, payload: list[object]) -> None:
        raw_name = payload[0]
        assert isinstance(raw_name, str) and raw_name.startswith("NAME:"), "material payload must start with NAME:<material>"
        material_name = raw_name.removeprefix("NAME:")
        material = self.materials.material_keys.get(material_name.casefold())
        if material is None:
            material = _FakeMaterial(material_name)
            self.materials.material_keys[material_name.casefold()] = material
        for index, item in enumerate(payload[:-1]):
            if item == "permittivity:=":
                material.permittivity = str(payload[index + 1])
            if item == "permeability:=":
                material.permeability = str(payload[index + 1])
            if item == "conductivity:=":
                material.conductivity = str(payload[index + 1])
            if item == "magnetic_loss_tangent:=":
                material.magnetic_loss_tangent = str(payload[index + 1])


class _FakeProject:
    def __init__(self, *, materials: _FakeMaterials) -> None:
        self.add_dataset_calls: list[list[object]] = []
        self.definition_manager = _FakeDefinitionManager(materials=materials)

    def AddDataset(self, payload: list[object]) -> object:
        self.add_dataset_calls.append(payload)
        return None

    def GetDefinitionManager(self) -> object:
        return self.definition_manager


class _FakeMeshModule:
    def __init__(self) -> None:
        self.assign_length_op_result: object = True
        self.assign_length_op_calls: list[list[object]] = []

    def AssignLengthOp(self, props: list[object]) -> object:
        self.assign_length_op_calls.append(list(props))
        return self.assign_length_op_result


class _FakeDesign:
    def __init__(self, *, mesh_module: _FakeMeshModule) -> None:
        self.mesh_module = mesh_module
        self.get_module_calls: list[str] = []
        self.import_dataset_calls: list[str] = []

    def GetModule(self, name: str) -> object:
        self.get_module_calls.append(name)
        if name != "MeshSetup":
            raise AssertionError(f"unexpected module lookup in fake design: {name}")
        return self.mesh_module

    def ImportDataset(self, path: str) -> object:
        self.import_dataset_calls.append(path)
        return None

    def ValidateDesign(self) -> object:
        return True


class _FakeModeler:
    def __init__(
        self,
        *,
        imported_name_batches: list[tuple[str, ...]],
        import_result: object = True,
    ) -> None:
        self._object_names: tuple[str, ...] = ("existing",)
        self._imported_name_batches = list(imported_name_batches)
        self._import_result = import_result
        self.import_calls: list[Path] = []
        self.import_kwargs_calls: list[dict[str, object]] = []
        self.create_polyline_calls: list[dict[str, object]] = []
        self.cover_lines_calls: list[str] = []
        self.create_group_calls: list[tuple[list[str], str]] = []
        self.model_state_calls: list[tuple[str, bool]] = []
        self.move_calls: list[tuple[list[str], list[float]]] = []
        self.objects: dict[str, _FakeObject] = {"existing": _FakeObject("existing")}
        self.created_region_name: str = ""
        self.created_region_pad_value: float = 0.0
        self.created_region_pad_type: str = ""
        self.create_polyline_returns_false = False
        self.cover_lines_returns_false = False
        self.create_region_returns_false = False
        self.get_object_faces_returns_false = False
        self.region_faces = [10, 11, 12, 13, 14, 15]

    @property
    def object_names(self) -> tuple[str, ...]:
        return self._object_names

    def import_3d_cad(self, input_file: str | Path, **kwargs: object) -> object:
        self.import_calls.append(Path(input_file))
        self.import_kwargs_calls.append(dict(kwargs))
        if self._import_result is not True:
            return self._import_result
        if not self._imported_name_batches:
            raise AssertionError("fake import batch queue exhausted")
        next_names = self._imported_name_batches.pop(0)
        self._object_names = self._object_names + next_names
        for name in next_names:
            self.objects[name] = _FakeObject(name)
        return True

    def set_object_model_state(self, name: str, model: bool) -> object:
        self.model_state_calls.append((name, model))
        return True

    def create_polyline(self, **kwargs: object) -> object:
        self.create_polyline_calls.append(dict(kwargs))
        if self.create_polyline_returns_false:
            return False
        name = kwargs["name"]
        assert isinstance(name, str)
        self.objects[name] = _FakeObject(name)
        if name not in self._object_names:
            self._object_names = self._object_names + (name,)
        return self.objects[name]

    def cover_lines(self, assignment: str) -> object:
        self.cover_lines_calls.append(assignment)
        if self.cover_lines_returns_false:
            return False
        self.objects[assignment] = _new_fake_sheet_object(assignment)
        return assignment

    def create_group(self, objects: list[str], group_name: str) -> str:
        self.create_group_calls.append((list(objects), group_name))
        return group_name

    def get_object_from_name(self, assignment: str) -> object:
        return self.objects[assignment]

    def move(self, assignment: object, vector: list[float]) -> object:
        assert isinstance(assignment, list)
        self.move_calls.append((list(assignment), list(vector)))
        return True

    class _Region:
        def __init__(self, name: str) -> None:
            self.name = name

    def create_region(self, pad_value: int, pad_type: str, name: str) -> object:
        self.created_region_pad_value = float(pad_value)
        self.created_region_pad_type = pad_type
        self.created_region_name = name
        if self.create_region_returns_false:
            return False
        return _FakeModeler._Region(name)

    def get_object_faces(self, assignment: str) -> object:
        if self.get_object_faces_returns_false:
            return False
        if assignment != self.created_region_name:
            return []
        return list(self.region_faces)


class _FakeDesktop:
    def __init__(self) -> None:
        self.release_calls: list[tuple[bool, bool]] = []
        self.messages: list[str] = []

    def release_desktop(self, close_projects: bool, close_on_exit: bool) -> object:
        self.release_calls.append((close_projects, close_on_exit))
        return True

    def GetMessages(self, project_name: str, design_name: str, level: int) -> list[str]:
        return list(self.messages)


class _FakeHfss:
    def __init__(self, *, modeler: _FakeModeler, save_project_result: object = True) -> None:
        self.modeler = modeler
        self.desktop_class = _FakeDesktop()
        self._save_project_result = save_project_result
        self.mesh_module = _FakeMeshModule()
        self.design = _FakeDesign(mesh_module=self.mesh_module)
        self.materials = _FakeMaterials()
        self.oproject = _FakeProject(materials=self.materials)
        self.design_name = "type2_step_import"
        self.insert_design_calls: list[str] = []
        self.save_project_calls: list[str] = []
        self.radiation_boundary_result = True
        self.radiation_boundary_calls: list[tuple[list[int], str]] = []
        self.radiation_assigned_faces: list[int] = []
        self.design_variables: dict[str, str] = {}

    @property
    def odesign(self) -> object:
        return self.design

    def save_project(self, path: str) -> object:
        self.save_project_calls.append(path)
        return self._save_project_result

    def __setitem__(self, key: str, value: str) -> None:
        self.design_variables[key] = value

    def insert_design(self, name: str | None = None, solution_type: str | None = None) -> str:
        _ = solution_type
        requested_name = self.design_name if name is None else name
        self.insert_design_calls.append(requested_name)
        inserted_name = f"{requested_name}_1"
        self.design_name = inserted_name
        self.modeler._object_names = ()
        self.modeler.objects = {}
        return inserted_name

    def assign_radiation_boundary_to_faces(self, assignment: object, name: str) -> object:
        assert isinstance(assignment, list)
        normalized = [int(face_id) for face_id in assignment]
        self.radiation_boundary_calls.append((normalized, name))
        self.radiation_assigned_faces.extend(normalized)
        return self.radiation_boundary_result


def _source_paths(tmp_path: Path) -> tuple[Path, Path]:
    scene_step = _write_step(tmp_path / "type2_scene.step")
    ledger_path = tmp_path / "type2_step_ledger.json"
    return (scene_step, ledger_path)


def _rx_single_coil_entry(tmp_path: Path) -> dict[str, object]:
    return _modeled_entry(
        object_id="rx_rect_void_coil",
        role="rx_single_coil",
        plane="YZ",
        placement_owner_id="rx_region_max",
        origin_xyz=(1.7, -25.0, 139.0),
        size_xyz=(2.8, 50.0, 30.0),
        source_metadata_path=str(tmp_path / "rx.metadata.json"),
    )


def _single_layer_modeled_objects(tmp_path: Path) -> list[dict[str, object]]:
    return [
        _modeled_entry(source_metadata_path=str(tmp_path / "tx.metadata.json")),
        _rx_single_coil_entry(tmp_path),
    ]


def _single_layer_imported_name_batch() -> tuple[str, ...]:
    return _single_layer_imported_name_batch_with_tx_region_actual_divisions(
        tx_region_actual_x_division_count=1,
        tx_region_actual_y_division_count=1,
    )


def _single_layer_imported_name_batch_with_tx_region_actual_divisions(
    *,
    tx_region_actual_x_division_count: int,
    tx_region_actual_y_division_count: int,
) -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    if tx_region_actual_x_division_count != 1 or tx_region_actual_y_division_count != 1:
        tx_region_actual_member_names = _tx_region_actual_member_names(
            x_division_count=tx_region_actual_x_division_count,
            y_division_count=tx_region_actual_y_division_count,
        )
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        "tx_pcb_l0",
        "tx_copper_l0",
        "rx_pcb_l0",
        "rx_copper_l0",
    )


def _tx_wall_expected_names(*, repeat_count: int) -> list[str]:
    if repeat_count == 0:
        return []
    return [
        "tx_wall_ferrite_u0",
        "tx_wall_pet_psa_u0",
        "tx_wall_air_u0",
    ]


def _rx_underlay_expected_names(*, repeat_count: int) -> list[str]:
    if repeat_count == 0:
        return []
    return [
        "under_rx_ferrite_u0",
        "under_rx_pet_psa_u0",
        "under_rx_air_u0",
    ]


def _single_layer_modeled_objects_with_role_aware_underlay(
    tmp_path: Path,
    *,
    tx_wall_repeat_count: int = 0,
    rx_repeat_count: int,
) -> list[dict[str, object]]:
    tx_expected_names = [
        "tx_pcb_l0",
        "tx_copper_l0",
        *_tx_wall_expected_names(repeat_count=tx_wall_repeat_count),
    ]
    rx_expected_names = ["rx_pcb_l0", "rx_copper_l0", *_rx_underlay_expected_names(repeat_count=rx_repeat_count)]
    return [
        _modeled_entry(
            source_metadata_path=str(tmp_path / "tx.metadata.json"),
            expected_names=tx_expected_names,
            expected_groups=_expected_ferrite_group_for_role(role="tx_single_coil", expected_names=tx_expected_names),
        ),
        _modeled_entry(
            object_id="rx_rect_void_coil",
            role="rx_single_coil",
            plane="YZ",
            placement_owner_id="rx_region_max",
            origin_xyz=(1.7, -25.0, 139.0),
            size_xyz=(2.8, 50.0, 30.0),
            source_metadata_path=str(tmp_path / "rx.metadata.json"),
            expected_names=rx_expected_names,
            expected_groups=_expected_ferrite_group_for_role(role="rx_single_coil", expected_names=rx_expected_names),
        ),
    ]


def _single_layer_imported_name_batch_with_role_aware_underlay(
    *,
    tx_wall_repeat_count: int = 0,
    rx_repeat_count: int,
) -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        "tx_pcb_l0",
        "tx_copper_l0",
        *_tx_wall_expected_names(repeat_count=tx_wall_repeat_count),
        "rx_pcb_l0",
        "rx_copper_l0",
        *_rx_underlay_expected_names(repeat_count=rx_repeat_count),
    )


def _tx_plate_stack_expected_names(
    *,
    turn_count: int = _PLATE_STACK_TURN_COUNT,
    pcb_total_thickness_mm: float = _PLATE_STACK_PCB_TOTAL_THICKNESS_MM,
) -> list[str]:
    return list(
        expected_plate_stack_body_names(
            role="tx_plate_stack",
            turn_count=turn_count,
            pcb_total_thickness_mm=pcb_total_thickness_mm,
        )
    )


def _rx_plate_stack_expected_names(
    *,
    turn_count: int = _PLATE_STACK_TURN_COUNT,
    pcb_total_thickness_mm: float = _PLATE_STACK_PCB_TOTAL_THICKNESS_MM,
) -> list[str]:
    return list(
        expected_plate_stack_body_names(
            role="rx_plate_stack",
            turn_count=turn_count,
            pcb_total_thickness_mm=pcb_total_thickness_mm,
        )
    )


def _ferrite_group_members_for_role(*, role: str, expected_names: list[str]) -> tuple[str, ...]:
    if role == "tx_plate_stack":
        return tuple(name for name in expected_names if name in _TX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES)
    if role == "rx_plate_stack":
        return tuple(name for name in expected_names if name in _RX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES)
    if role.startswith("tx_"):
        member_prefixes = _TX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES
        return tuple(name for name in expected_names if name.startswith(member_prefixes))
    if role.startswith("rx_"):
        member_prefixes = _RX_SINGLE_COIL_FERRITE_GROUP_MEMBER_PREFIXES
        return tuple(name for name in expected_names if name.startswith(member_prefixes))
    raise ValueError(f"unsupported ferrite group role in test helper: {role!r}")


def _legacy_tx_plate_stack_expected_names() -> list[str]:
    expected_names = _tx_plate_stack_expected_names()
    renamed: list[str] = []
    for name in expected_names:
        if name == "tx_stack_pet_psa":
            renamed.append("tx_stack_pet_psa_u0")
            continue
        if name == "tx_stack_ferrite":
            renamed.append("tx_stack_ferrite_u0")
            continue
        if name == "tx_stack_air":
            renamed.append("tx_stack_air_u0")
            continue
        renamed.append(name)
    return renamed


def _legacy_tx_plate_stack_imported_name_batch() -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        *_legacy_tx_plate_stack_expected_names(),
    )


def _expected_ferrite_group_for_role(*, role: str, expected_names: list[str]) -> list[ExportedBodyGroup]:
    member_body_names = _ferrite_group_members_for_role(role=role, expected_names=expected_names)
    if role == "tx_plate_stack":
        return [
            {"group_name": _TX_COPPER_GROUP_NAME, "member_body_names": (_TX_PLATE_COPPER_NAME,)},
            {"group_name": _TX_FERRITE_GROUP_NAME, "member_body_names": member_body_names},
        ]
    if role == "rx_plate_stack":
        return [
            {"group_name": _RX_COPPER_GROUP_NAME, "member_body_names": (_RX_PLATE_COPPER_NAME,)},
            {"group_name": _RX_FERRITE_GROUP_NAME, "member_body_names": member_body_names},
        ]
    if len(member_body_names) == 0:
        return []
    if role.startswith("tx_"):
        return [{"group_name": _TX_FERRITE_GROUP_NAME, "member_body_names": member_body_names}]
    if role.startswith("rx_"):
        return [{"group_name": _RX_FERRITE_GROUP_NAME, "member_body_names": member_body_names}]
    raise ValueError(f"unsupported ferrite group role in test helper: {role!r}")


def _tx_plate_stack_expected_groups(
) -> list[ExportedBodyGroup]:
    expected_names = _tx_plate_stack_expected_names()
    return _expected_ferrite_group_for_role(role="tx_plate_stack", expected_names=expected_names)


def _rx_plate_stack_expected_groups(
) -> list[ExportedBodyGroup]:
    expected_names = _rx_plate_stack_expected_names()
    return _expected_ferrite_group_for_role(role="rx_plate_stack", expected_names=expected_names)


def _plate_stack_modeled_entry(
    *,
    object_id: str,
    role: str,
    plane: str,
    placement_owner_id: str,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
    source_metadata_path: str,
    expected_names: list[str],
    expected_groups: list[ExportedBodyGroup],
    pcb_layer_positions_mm: list[float],
    copper_layer_positions_mm: list[float],
    terminal_metadata: dict[str, object],
) -> dict[str, object]:
    origin_x, origin_y, origin_z = origin_xyz
    size_x, size_y, size_z = size_xyz
    return {
        "object_id": object_id,
        "role": role,
        "plane": plane,
        "placement_owner_id": placement_owner_id,
        "material": "composite",
        "model_state": True,
        "expected_exported_body_names": expected_names,
        "expected_exported_body_count": len(expected_names),
        "expected_exported_body_groups": expected_groups,
        "canonical_coordinates": {
            "frame_origin_xyz": [origin_x, origin_y, origin_z],
            "outer_bounds_min_xyz": [origin_x, origin_y, origin_z],
            "outer_bounds_max_xyz": [origin_x + size_x, origin_y + size_y, origin_z + size_z],
            "outer_bounds_size_xyz": [size_x, size_y, size_z],
            "pcb_layer_z_positions_mm": pcb_layer_positions_mm,
            "copper_layer_z_positions_mm": copper_layer_positions_mm,
        },
        "terminal_metadata": terminal_metadata,
        "source_metadata_path": source_metadata_path,
    }


def _plate_stack_terminal_metadata(
    *,
    owner_origin_y: float,
    owner_size_y: float,
    owner_origin_z: float,
    owner_size_z: float,
    copper_thickness_mm: float,
    turn_count: int = _PLATE_STACK_TURN_COUNT,
    metal_fill_factor: float = 0.4,
    prefix: str,
) -> dict[str, object]:
    pitch_z = owner_size_z / float(turn_count)
    trace_height_z = pitch_z * metal_fill_factor
    conductor_origin_z = owner_origin_z
    input_origin_z = conductor_origin_z
    output_origin_z = conductor_origin_z + (pitch_z * float(turn_count - 1))
    sheet_y = owner_origin_y - _PLATE_STACK_STUB_LENGTH_MM
    z_min = input_origin_z
    z_max = output_origin_z + trace_height_z
    return {
        "kind": "stub_port",
        "input_stub_body_name": f"{prefix}_stub_in",
        "output_stub_body_name": f"{prefix}_stub_out",
        "start_point_plane_mm": [sheet_y, input_origin_z + (trace_height_z / 2.0)],
        "end_point_plane_mm": [sheet_y, output_origin_z + (trace_height_z / 2.0)],
        "port_sheet_vertices_xyz": [
            [0.0, sheet_y, z_min],
            [copper_thickness_mm, sheet_y, z_min],
            [copper_thickness_mm, sheet_y, z_max],
            [0.0, sheet_y, z_max],
        ],
    }


def _tx_plate_stack_entry(tmp_path: Path) -> dict[str, object]:
    return _plate_stack_modeled_entry(
        object_id="tx_plate_stack",
        role="tx_plate_stack",
        plane="YZ",
        placement_owner_id="tx_region",
        origin_xyz=(0.0, -145.0, 0.0),
        size_xyz=(6.9, 285.0, 90.0),
        source_metadata_path=str(tmp_path / "tx_plate_stack.metadata.json"),
        expected_names=_tx_plate_stack_expected_names(),
        expected_groups=_tx_plate_stack_expected_groups(),
        pcb_layer_positions_mm=[0.035, 5.3],
        copper_layer_positions_mm=[0.0, 6.865],
        terminal_metadata=_plate_stack_terminal_metadata(
            owner_origin_y=-140.0,
            owner_size_y=280.0,
            owner_origin_z=0.0,
            owner_size_z=90.0,
            copper_thickness_mm=0.035,
            prefix="tx",
        ),
    )


def _rx_plate_stack_entry(tmp_path: Path) -> dict[str, object]:
    return _plate_stack_modeled_entry(
        object_id="rx_plate_stack",
        role="rx_plate_stack",
        plane="YZ",
        placement_owner_id="rx_region_max",
        origin_xyz=(0.0, -285.0, 139.0),
        size_xyz=(4.5, 565.0, 360.0),
        source_metadata_path=str(tmp_path / "rx_plate_stack.metadata.json"),
        expected_names=_rx_plate_stack_expected_names(),
        expected_groups=_rx_plate_stack_expected_groups(),
        pcb_layer_positions_mm=[0.1, 4.1],
        copper_layer_positions_mm=[0.0, 4.4],
        terminal_metadata=_plate_stack_terminal_metadata(
            owner_origin_y=-280.0,
            owner_size_y=560.0,
            owner_origin_z=139.0,
            owner_size_z=360.0,
            copper_thickness_mm=0.1,
            prefix="rx",
        ),
    )


def _plate_stack_modeled_objects(tmp_path: Path) -> list[dict[str, object]]:
    return [
        _tx_plate_stack_entry(tmp_path),
        _rx_plate_stack_entry(tmp_path),
    ]


def _plate_stack_imported_name_batch() -> tuple[str, ...]:
    tx_region_actual_member_names = _tx_region_actual_member_names()
    return (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        *_tx_plate_stack_expected_names(),
        *_rx_plate_stack_expected_names(),
    )


def _plate_stack_imported_name_batch_with_tx_solid_drift() -> tuple[str, ...]:
    imported_names = [name for name in _plate_stack_imported_name_batch() if name != "tx_stack_pet_psa"]
    imported_names.append("SOLID_317")
    return tuple(imported_names)


def _plate_stack_imported_name_batch_with_rx_solid_drift() -> tuple[str, ...]:
    imported_names = [name for name in _plate_stack_imported_name_batch() if name != "rx_stack_ferrite"]
    imported_names.append("SOLID_911")
    return tuple(imported_names)


def _tx_plate_stack_array_expected_names(*, branch_count: int) -> list[str]:
    names: list[str] = [_TX_PLATE_COPPER_NAME]
    for index in range(branch_count):
        names.extend(
            (
                f"tx_b{index}_pcb_wall",
                f"tx_b{index}_stack_pet_psa",
                f"tx_b{index}_stack_ferrite",
                f"tx_b{index}_stack_air",
                f"tx_b{index}_pcb_coil",
            )
        )
    return names


def _tx_plate_stack_array_expected_groups(*, branch_count: int) -> list[ExportedBodyGroup]:
    ferrite_members = tuple(
        name
        for name in _tx_plate_stack_array_expected_names(branch_count=branch_count)
        if name.endswith("_stack_pet_psa")
        or name.endswith("_stack_ferrite")
        or name.endswith("_stack_air")
    )
    return [
        {
            "group_name": _TX_COPPER_GROUP_NAME,
            "member_body_names": (_TX_PLATE_COPPER_NAME,),
        },
        {"group_name": _TX_FERRITE_GROUP_NAME, "member_body_names": ferrite_members},
    ]


def _expected_mesh_length_payload(*, tx_object_name: str = "tx_copper_l0") -> list[object]:
    return [
        "NAME:Length1",
        "RefineInside:=",
        False,
        "Enabled:=",
        True,
        "Objects:=",
        [tx_object_name, "rx_copper_l0"],
        "RestrictElem:=",
        False,
        "NumMaxElem:=",
        "1000",
        "RestrictLength:=",
        True,
        "MaxLength:=",
        "5mm",
    ]


def test_import_type2_step_ledger_imports_single_scene_and_writes_partitioned_ledger(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
        radiation_margin_mm=4123.0,
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_single_layer_imported_name_batch()]))

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.modeler.import_calls == [scene_step]
    assert session.modeler.import_kwargs_calls == [{"import_free_surfaces": False, "create_group": False}]
    tx_region_actual_member_names = _tx_region_actual_member_names()
    assert session.modeler.model_state_calls == [
        ("environment", False),
        ("tx_region", False),
        *((name, False) for name in tx_region_actual_member_names),
        ("rx_region_max", False),
        ("tx_pcb_l0", True),
        ("tx_copper_l0", True),
        ("tx_port_sheet", True),
        ("rx_pcb_l0", True),
        ("rx_copper_l0", True),
        ("rx_port_sheet", True),
    ]
    assert session.modeler.objects["tx_copper_l0"].material_name == "copper"
    assert session.modeler.objects["rx_copper_l0"].material_name == "copper"
    assert session.design.import_dataset_calls == []
    assert session.oproject.add_dataset_calls == []
    assert session.oproject.definition_manager.add_material_calls == []
    assert session.design.get_module_calls == []
    assert session.mesh_module.assign_length_op_calls == []
    assert session.modeler.created_region_name == ""
    assert session.radiation_boundary_calls == []
    assert session.save_project_calls == [str(output_aedt_path)]
    assert session.desktop_class.release_calls == [(True, True)]
    assert "mesh" not in result
    assert "boundary" not in result
    modeled_by_id = {entry["object_id"]: entry for entry in result["modeled_objects"]}
    assert modeled_by_id["tx_rect_void_coil"]["imported_object_names"] == ["tx_pcb_l0", "tx_copper_l0", "tx_port_sheet"]
    assert modeled_by_id["rx_rect_void_coil"]["imported_object_names"] == ["rx_pcb_l0", "rx_copper_l0", "rx_port_sheet"]
    written = json.loads(imported_ledger_path.read_text(encoding="utf-8"))
    assert written == result


def test_import_type2_step_ledger_accepts_tiled_tx_region_actual_member_names(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    tx_region_actual_x_division_count = 3
    tx_region_actual_y_division_count = 3
    tx_region_actual_member_names = _tx_region_actual_member_names(
        x_division_count=tx_region_actual_x_division_count,
        y_division_count=tx_region_actual_y_division_count,
    )
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[
            _non_model_entry(
                tx_region_actual_x_division_count=tx_region_actual_x_division_count,
                tx_region_actual_y_division_count=tx_region_actual_y_division_count,
            )
        ],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[
                _single_layer_imported_name_batch_with_tx_region_actual_divisions(
                    tx_region_actual_x_division_count=tx_region_actual_x_division_count,
                    tx_region_actual_y_division_count=tx_region_actual_y_division_count,
                )
            ]
        )
    )

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
        imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    expected_non_model_model_state_calls = [
        ("environment", False),
        ("tx_region", False),
        *((name, False) for name in tx_region_actual_member_names),
        ("rx_region_max", False),
    ]
    assert session.modeler.model_state_calls[: len(expected_non_model_model_state_calls)] == expected_non_model_model_state_calls
    imported_non_model_entry = result["non_model_objects"][0]
    assert tuple(cast(list[str], imported_non_model_entry["member_object_ids"])) == (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
    )
    assert imported_non_model_entry["imported_object_names"] == [
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
    ]


def test_import_type2_step_ledger_allows_missing_optional_port_sheet_bodies(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[
                (
                    "environment",
                    "tx_region",
                    *_tx_region_actual_member_names(),
                    "rx_region_max",
                    "tx_pcb_l0",
                    "tx_copper_l0",
                    "rx_pcb_l0",
                    "rx_copper_l0",
                )
            ]
        )
    )

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
        imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    modeled_by_id = {entry["object_id"]: entry for entry in result["modeled_objects"]}
    assert modeled_by_id["tx_rect_void_coil"]["imported_object_names"] == ["tx_pcb_l0", "tx_copper_l0", "tx_port_sheet"]
    assert modeled_by_id["rx_rect_void_coil"]["imported_object_names"] == ["rx_pcb_l0", "rx_copper_l0", "rx_port_sheet"]
    assert session.mesh_module.assign_length_op_calls == []
    assert session.radiation_boundary_calls == []
    assert "mesh" not in result
    assert "boundary" not in result


def test_import_type2_step_ledger_leaves_tx_rect_void_columns_port_sheet_to_setup_ready(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_tx_rect_void_columns_non_model_entry_for_import()],
        modeled_objects=[_tx_rect_void_columns_entry_for_import(tmp_path)],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[_tx_rect_void_columns_imported_name_batch_for_import()]
        )
    )

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.modeler.create_polyline_calls == []
    assert session.modeler.cover_lines_calls == []
    modeled_by_id = {entry["object_id"]: entry for entry in result["modeled_objects"]}
    assert modeled_by_id["tx_rect_void_columns"]["imported_object_names"] == [
        "txrvc_x0_y0_pcb_l0",
        "tx_rect_void_columns_copper",
    ]


def test_import_type2_step_ledger_styles_role_aware_underlay_and_keeps_mesh_conductor_only(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects_with_role_aware_underlay(
            tmp_path,
            tx_wall_repeat_count=2,
            rx_repeat_count=1,
        ),
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[
                _single_layer_imported_name_batch_with_role_aware_underlay(
                    tx_wall_repeat_count=2,
                    rx_repeat_count=1,
                )
            ]
        )
    )
    session.materials.delayed_lookup_material_names.add("PET_PSA")

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.design.import_dataset_calls == [str(Path(__file__).resolve().parents[2] / "notebooks" / "mu_p.tab")]
    assert len(session.oproject.add_dataset_calls) == 2
    assert session.oproject.definition_manager.add_material_calls[0][0] == "NAME:MULL12060ferrite"
    assert session.materials.material_keys["mull12060ferrite"].permittivity == "6"
    assert session.materials.aedmattolibrary_calls == ["PET_PSA"]
    assert session.materials.material_keys["pet_psa"].permittivity == "2.8"
    assert session.modeler.objects["tx_wall_ferrite_u0"].material_name == "MULL12060ferrite"
    assert session.modeler.objects["tx_wall_pet_psa_u0"].material_name == "PET_PSA"
    assert session.modeler.objects["tx_wall_air_u0"].material_name == "vacuum"
    assert session.modeler.objects["under_rx_ferrite_u0"].material_name == "MULL12060ferrite"
    assert session.modeler.objects["under_rx_pet_psa_u0"].material_name == "PET_PSA"
    assert session.modeler.objects["under_rx_air_u0"].material_name == "vacuum"
    assert session.mesh_module.assign_length_op_calls == []
    assert "mesh" not in result
    assert "boundary" not in result
    modeled_by_id = {entry["object_id"]: entry for entry in result["modeled_objects"]}
    assert modeled_by_id["tx_rect_void_coil"]["imported_object_names"] == [
        "tx_pcb_l0",
        "tx_copper_l0",
        "tx_wall_ferrite_u0",
        "tx_wall_pet_psa_u0",
        "tx_wall_air_u0",
        "tx_port_sheet",
    ]
    assert modeled_by_id["rx_rect_void_coil"]["imported_object_names"] == [
        "rx_pcb_l0",
        "rx_copper_l0",
        "under_rx_ferrite_u0",
        "under_rx_pet_psa_u0",
        "under_rx_air_u0",
        "rx_port_sheet",
    ]
    assert modeled_by_id["tx_rect_void_coil"]["imported_body_groups"] == [
        {
            "group_name": _TX_FERRITE_GROUP_NAME,
            "member_object_names": [
                "tx_wall_ferrite_u0",
                "tx_wall_pet_psa_u0",
                "tx_wall_air_u0",
            ],
        }
    ]
    assert modeled_by_id["rx_rect_void_coil"]["imported_body_groups"] == [
        {
            "group_name": _RX_FERRITE_GROUP_NAME,
            "member_object_names": [
                "under_rx_ferrite_u0",
                "under_rx_pet_psa_u0",
                "under_rx_air_u0",
            ],
        }
    ]
    assert session.modeler.create_group_calls == [
        (
            ["tx_wall_ferrite_u0", "tx_wall_pet_psa_u0", "tx_wall_air_u0"],
            _TX_FERRITE_GROUP_NAME,
        ),
        (
            ["under_rx_ferrite_u0", "under_rx_pet_psa_u0", "under_rx_air_u0"],
            _RX_FERRITE_GROUP_NAME,
        ),
    ]
    written = json.loads(imported_ledger_path.read_text(encoding="utf-8"))
    assert written == result


def test_import_type2_step_ledger_accepts_tx_and_rx_plate_stack_geometry_only_roles(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=_plate_stack_modeled_objects(tmp_path),
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(imported_name_batches=[_plate_stack_imported_name_batch()])
    )
    session.materials.delayed_lookup_material_names.add("PET_PSA")

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.modeler.import_calls == [scene_step]
    assert session.modeler.import_kwargs_calls == [{"import_free_surfaces": False, "create_group": False}]
    assert [call["name"] for call in session.modeler.create_polyline_calls] == [
        "tx_plate_port_sheet",
        "rx_plate_port_sheet",
    ]
    assert session.modeler.cover_lines_calls == ["tx_plate_port_sheet", "rx_plate_port_sheet"]
    assert session.design.import_dataset_calls == [str(Path(__file__).resolve().parents[2] / "notebooks" / "mu_p.tab")]
    assert len(session.oproject.add_dataset_calls) == 2
    assert session.materials.aedmattolibrary_calls == ["PET_PSA"]
    assert session.modeler.objects["tx_stack_ferrite"].material_name == "MULL12060ferrite"
    assert session.modeler.objects["tx_stack_pet_psa"].material_name == "PET_PSA"
    assert session.modeler.objects["tx_stack_air"].material_name == "vacuum"
    assert session.modeler.objects["rx_stack_ferrite"].material_name == "MULL12060ferrite"
    assert session.modeler.objects["rx_stack_pet_psa"].material_name == "PET_PSA"
    assert session.modeler.objects["rx_stack_air"].material_name == "vacuum"
    assert session.mesh_module.assign_length_op_calls == []
    assert session.radiation_boundary_calls == []
    assert "mesh" not in result
    assert "boundary" not in result
    modeled_by_id = {entry["object_id"]: entry for entry in result["modeled_objects"]}
    tx_imported_object_names = cast(list[str], modeled_by_id["tx_plate_stack"]["imported_object_names"])
    rx_imported_object_names = cast(list[str], modeled_by_id["rx_plate_stack"]["imported_object_names"])
    tx_ferrite_family_imported_names = [name for name in tx_imported_object_names if name.startswith("tx_stack_")]
    rx_ferrite_family_imported_names = [name for name in rx_imported_object_names if name.startswith("rx_stack_")]
    assert tx_ferrite_family_imported_names == list(_TX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES)
    assert rx_ferrite_family_imported_names == list(_RX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES)
    assert all(not name.startswith("SOLID") for name in [*tx_imported_object_names, *rx_imported_object_names])
    assert modeled_by_id["tx_plate_stack"]["imported_object_names"] == [
        *_tx_plate_stack_expected_names(),
        "tx_plate_port_sheet",
    ]
    assert modeled_by_id["tx_plate_stack"]["imported_body_groups"] == [
        {
            "group_name": cast(str, group_entry["group_name"]),
            "member_object_names": list(cast(tuple[str, ...], group_entry["member_body_names"])),
        }
        for group_entry in _tx_plate_stack_expected_groups()
    ]
    assert cast(dict[str, object], modeled_by_id["tx_plate_stack"]["terminal_metadata"])["kind"] == "stub_port"
    assert modeled_by_id["rx_plate_stack"]["imported_object_names"] == [
        *_rx_plate_stack_expected_names(),
        "rx_plate_port_sheet",
    ]
    assert modeled_by_id["rx_plate_stack"]["imported_body_groups"] == [
        {
            "group_name": cast(str, group_entry["group_name"]),
            "member_object_names": list(cast(tuple[str, ...], group_entry["member_body_names"])),
        }
        for group_entry in _rx_plate_stack_expected_groups()
    ]
    assert cast(dict[str, object], modeled_by_id["rx_plate_stack"]["terminal_metadata"])["kind"] == "stub_port"
    assert session.modeler.create_group_calls == [
        (
            list(cast(tuple[str, ...], group_entry["member_body_names"])),
            cast(str, group_entry["group_name"]),
        )
        for group_entry in _tx_plate_stack_expected_groups()
    ] + [
        (
            list(cast(tuple[str, ...], group_entry["member_body_names"])),
            cast(str, group_entry["group_name"]),
        )
        for group_entry in _rx_plate_stack_expected_groups()
    ]
    written = json.loads(imported_ledger_path.read_text(encoding="utf-8"))
    assert written == result


def test_import_type2_step_ledger_accepts_plate_stack_partial_z_usage_windows(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    tx_entry = _tx_plate_stack_entry(tmp_path)
    tx_coordinates = cast(dict[str, object], tx_entry["canonical_coordinates"])
    tx_coordinates["outer_bounds_min_xyz"] = [0.0, -145.0, 39.20625]
    tx_coordinates["outer_bounds_max_xyz"] = [6.9, 140.0, 90.0]
    tx_coordinates["outer_bounds_size_xyz"] = [6.9, 285.0, 50.79375]
    tx_entry["terminal_metadata"] = _plate_stack_terminal_metadata(
        owner_origin_y=-140.0,
        owner_size_y=280.0,
        owner_origin_z=39.20625,
        owner_size_z=50.79375,
        copper_thickness_mm=0.035,
        prefix="tx",
    )
    rx_entry = _rx_plate_stack_entry(tmp_path)
    rx_coordinates = cast(dict[str, object], rx_entry["canonical_coordinates"])
    rx_coordinates["outer_bounds_min_xyz"] = [0.0, -285.0, 139.0]
    rx_coordinates["outer_bounds_max_xyz"] = [4.5, 280.0, 342.175]
    rx_coordinates["outer_bounds_size_xyz"] = [4.5, 565.0, 203.175]
    rx_entry["terminal_metadata"] = _plate_stack_terminal_metadata(
        owner_origin_y=-280.0,
        owner_size_y=560.0,
        owner_origin_z=139.0,
        owner_size_z=203.175,
        copper_thickness_mm=0.1,
        prefix="rx",
    )
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=[tx_entry, rx_entry],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_plate_stack_imported_name_batch()]))
    session.materials.delayed_lookup_material_names.add("PET_PSA")

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    modeled_by_id = {entry["object_id"]: entry for entry in result["modeled_objects"]}
    assert modeled_by_id["tx_plate_stack"]["canonical_coordinates"] == tx_coordinates
    assert modeled_by_id["rx_plate_stack"]["canonical_coordinates"] == rx_coordinates


def test_import_type2_step_ledger_accepts_plate_stack_partial_y_usage_windows(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    tx_entry = _tx_plate_stack_entry(tmp_path)
    tx_coordinates = cast(dict[str, object], tx_entry["canonical_coordinates"])
    tx_coordinates["outer_bounds_min_xyz"] = [0.0, -65.0, 0.0]
    tx_coordinates["outer_bounds_max_xyz"] = [6.9, 60.0, 90.0]
    tx_coordinates["outer_bounds_size_xyz"] = [6.9, 125.0, 90.0]
    tx_entry["terminal_metadata"] = _plate_stack_terminal_metadata(
        owner_origin_y=-60.0,
        owner_size_y=120.0,
        owner_origin_z=0.0,
        owner_size_z=90.0,
        copper_thickness_mm=0.035,
        prefix="tx",
    )

    rx_entry = _rx_plate_stack_entry(tmp_path)
    rx_coordinates = cast(dict[str, object], rx_entry["canonical_coordinates"])
    rx_coordinates["outer_bounds_min_xyz"] = [0.0, -205.0, 139.0]
    rx_coordinates["outer_bounds_max_xyz"] = [4.5, 200.0, 499.0]
    rx_coordinates["outer_bounds_size_xyz"] = [4.5, 405.0, 360.0]
    rx_entry["terminal_metadata"] = _plate_stack_terminal_metadata(
        owner_origin_y=-200.0,
        owner_size_y=400.0,
        owner_origin_z=139.0,
        owner_size_z=360.0,
        copper_thickness_mm=0.1,
        prefix="rx",
    )
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=[tx_entry, rx_entry],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_plate_stack_imported_name_batch()]))
    session.materials.delayed_lookup_material_names.add("PET_PSA")

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    modeled_by_id = {entry["object_id"]: entry for entry in result["modeled_objects"]}
    assert modeled_by_id["tx_plate_stack"]["canonical_coordinates"] == tx_coordinates
    assert modeled_by_id["rx_plate_stack"]["canonical_coordinates"] == rx_coordinates


def test_import_type2_step_ledger_rejects_plate_stack_tx_off_center_active_y_window(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    tx_entry = _tx_plate_stack_entry(tmp_path)
    tx_coordinates = cast(dict[str, object], tx_entry["canonical_coordinates"])
    tx_coordinates["outer_bounds_min_xyz"] = [0.0, -140.0, 0.0]
    tx_coordinates["outer_bounds_max_xyz"] = [6.9, 145.0, 90.0]
    tx_coordinates["outer_bounds_size_xyz"] = [6.9, 285.0, 90.0]
    tx_entry["terminal_metadata"] = _plate_stack_terminal_metadata(
        owner_origin_y=-180.0,
        owner_size_y=360.0,
        owner_origin_z=0.0,
        owner_size_z=90.0,
        copper_thickness_mm=0.035,
        prefix="tx",
    )

    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=[tx_entry, _rx_plate_stack_entry(tmp_path)],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_plate_stack_imported_name_batch()]))
    session.materials.delayed_lookup_material_names.add("PET_PSA")

    with pytest.raises(ValueError, match=r"tx_plate_stack active Y footprint must be centered on global Y=0"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_rejects_legacy_plate_stack_u_names(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    tx_entry = _tx_plate_stack_entry(tmp_path)
    tx_entry["expected_exported_body_names"] = _legacy_tx_plate_stack_expected_names()
    tx_entry["expected_exported_body_count"] = len(_legacy_tx_plate_stack_expected_names())
    tx_entry["expected_exported_body_groups"] = []
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[tx_entry],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(imported_name_batches=[_legacy_tx_plate_stack_imported_name_batch()])
    )

    with pytest.raises(ValueError, match=r"must include tx plate-stack ferrite-family members"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_rejects_plate_stack_missing_copper_group(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _plate_stack_modeled_objects(tmp_path)
    tx_entry = cast(dict[str, object], modeled_objects[0])
    tx_groups = cast(list[dict[str, object]], tx_entry["expected_exported_body_groups"])
    tx_entry["expected_exported_body_groups"] = [tx_groups[1]]
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=modeled_objects,
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_plate_stack_imported_name_batch()]))

    with pytest.raises(ValueError, match=r"must match required role group contract"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_rejects_plate_stack_legacy_segment_leakage(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _plate_stack_modeled_objects(tmp_path)
    tx_entry = cast(dict[str, object], modeled_objects[0])
    tx_expected_names = cast(list[str], tx_entry["expected_exported_body_names"])
    tx_expected_names.append("tx_copper_wall_t0")
    tx_entry["expected_exported_body_count"] = len(tx_expected_names)
    tx_entry["expected_exported_body_groups"] = [
        {"group_name": _TX_COPPER_GROUP_NAME, "member_body_names": (_TX_PLATE_COPPER_NAME,)},
        {"group_name": _TX_FERRITE_GROUP_NAME, "member_body_names": _TX_PLATE_STACK_FERRITE_GROUP_MEMBER_NAMES},
    ]
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=modeled_objects,
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_plate_stack_imported_name_batch()]))

    with pytest.raises(ValueError, match=r"legacy plate-stack copper segment names"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


@pytest.mark.parametrize(
    ("imported_batch", "match"),
    [
        (
            _plate_stack_imported_name_batch_with_tx_solid_drift(),
            (
                r"missing required modeled body name \(object_id=tx_plate_stack, body_name=tx_stack_pet_psa\); "
                r"detected generic SOLID\* modeled names, which is an export-contract violation"
            ),
        ),
        (
            _plate_stack_imported_name_batch_with_rx_solid_drift(),
            (
                r"missing required modeled body name \(object_id=rx_plate_stack, body_name=rx_stack_ferrite\); "
                r"detected generic SOLID\* modeled names, which is an export-contract violation"
            ),
        ),
    ],
)
def test_import_type2_step_ledger_rejects_plate_stack_solid_name_drift(
    tmp_path: Path,
    imported_batch: tuple[str, ...],
    match: str,
) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_plate_stack_modeled_objects(tmp_path),
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[imported_batch]))

    with pytest.raises(ValueError, match=match):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_accepts_tx_plate_stack_array_exact_names(tmp_path: Path) -> None:
    branch_count = 3
    scene_step, ledger_path = _source_paths(tmp_path)
    modeled_objects = _plate_stack_modeled_objects(tmp_path)
    tx_entry = cast(dict[str, object], modeled_objects[0])
    tx_entry["expected_exported_body_names"] = _tx_plate_stack_array_expected_names(branch_count=branch_count)
    tx_entry["expected_exported_body_count"] = len(cast(list[str], tx_entry["expected_exported_body_names"]))
    tx_entry["expected_exported_body_groups"] = _tx_plate_stack_array_expected_groups(branch_count=branch_count)
    tx_terminal = cast(dict[str, object], tx_entry["terminal_metadata"])
    tx_vertices = cast(list[list[float]], tx_terminal["port_sheet_vertices_xyz"])
    tx_vertices[1][0] = 80.0
    tx_vertices[2][0] = 80.0
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=modeled_objects,
    )
    tx_expected_names = cast(list[str], tx_entry["expected_exported_body_names"])
    tx_region_actual_member_names = _tx_region_actual_member_names()
    imported_names = (
        "environment",
        "tx_region",
        *tx_region_actual_member_names,
        "rx_region_max",
        *tx_expected_names,
        *_rx_plate_stack_expected_names(),
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[tuple(imported_names)]))

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
        imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    imported_tx_entry = next(entry for entry in result["modeled_objects"] if entry["object_id"] == "tx_plate_stack")
    imported_tx_names = cast(list[str], imported_tx_entry["imported_object_names"])
    assert "tx_plate_copper" in imported_tx_names
    assert "tx_b0_pcb_wall" in imported_tx_names
    assert "tx_b2_stack_ferrite" in imported_tx_names
    assert "tx_pcb_wall" not in imported_tx_names
    created_polyline_names = [cast(str, call["name"]) for call in session.modeler.create_polyline_calls]
    assert created_polyline_names == ["tx_plate_port_sheet", "rx_plate_port_sheet"]


def test_import_type2_step_ledger_fails_unclaimed_solid_name_as_export_contract_violation(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[
                ("environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max", "tx_pcb_l0", "tx_copper_l0", "tx_port_sheet", "SOLID_404")
            ]
        )
    )

    with pytest.raises(
        ValueError,
        match=r"generic SOLID\* names that do not map to ledger ownership; this is an export-contract violation",
    ):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_styles_multilayer_tx_parallel_stack_before_mesh_validation_fails(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[
            _modeled_entry(
                expected_names=["tx_pcb_l0", "tx_pcb_l1", "tx_copper_stack"],
                pcb_layer_positions_mm=[87.2, 91.3],
                copper_layer_positions_mm=[88.8, 92.9],
            ),
        ],
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max", "tx_pcb_l0", "tx_pcb_l1", "tx_copper_stack")]
        )
    )

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    assert session.modeler.objects["tx_pcb_l0"].material_name == "FR4_epoxy"
    assert session.modeler.objects["tx_pcb_l1"].material_name == "FR4_epoxy"
    assert session.modeler.objects["tx_copper_stack"].material_name == "copper"
    assert session.mesh_module.assign_length_op_calls == []
    assert session.radiation_assigned_faces == []
    assert session.save_project_calls == [str(output_aedt_path)]
    assert "mesh" not in result
    assert "boundary" not in result


def test_import_type2_step_ledger_fails_when_modeled_labels_are_not_preserved(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[("environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max", "SOLID_7", "tx_copper_l0")]))

    with pytest.raises(ValueError, match=r"missing required modeled body name"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_scene_import_contains_unclaimed_object(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(
        modeler=_FakeModeler(
            imported_name_batches=[("environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max", "tx_pcb_l0", "tx_copper_l0", "tx_port_sheet", "mystery")]
        )
    )

    with pytest.raises(ValueError, match=r"unclaimed imported object names"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_scene_import_missing_non_model_member_name(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[("environment", "tx_region", "tx_pcb_l0", "tx_copper_l0")]))

    with pytest.raises(ValueError, match=r"missing non-model member object names"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_modeled_tx_is_not_centered_on_tx_region_y(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry(origin_xyz=(0.0, -16.0, 87.2))],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[("environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]))

    with pytest.raises(ValueError, match=r"center_y must already align with tx_region center_y"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_modeled_tx_does_not_touch_tx_region_min_x(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry(origin_xyz=(0.1, -15.0, 87.2))],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[("environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]))

    with pytest.raises(ValueError, match=r"outer bounds min_x must already touch tx_region min_x"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_modeled_tx_does_not_fit_tx_region(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry(size_xyz=(170.0, 30.0, 2.8))],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[("environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]))

    with pytest.raises(ValueError, match=r"outer bounds must fit inside tx_region"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_fails_when_modeled_tx_is_not_top_aligned_to_tx_region(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry(origin_xyz=(0.0, -15.0, 87.1))],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[("environment", "tx_region", *_tx_region_actual_member_names(), "rx_region_max", "tx_pcb_l0", "tx_copper_l0")]))

    with pytest.raises(ValueError, match=r"outer bounds max_z must already touch tx_region max_z"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_into_hfss_auto_detaches_after_import(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    output_aedt_path = tmp_path / "aedt" / "type2_import.aedt"
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_single_layer_imported_name_batch()]))

    result = import_type2_step_ledger_into_hfss(
        hfss=cast(HfssSession, session),
        step_ledger_path=ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
    )

    assert result["aedt_path"] == str(output_aedt_path)
    assert session.insert_design_calls == ["type2_step_import"]
    assert session.design_name == "type2_step_import_1"
    assert session.save_project_calls == [str(output_aedt_path)]
    assert session.design.get_module_calls == []
    assert session.mesh_module.assign_length_op_calls == []
    assert session.modeler.created_region_name == ""
    assert session.radiation_assigned_faces == []
    assert "mesh" not in result
    assert "boundary" not in result
    assert session.desktop_class.release_calls == [(False, False)]


def test_import_type2_step_ledger_into_hfss_releases_desktop_when_import_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[], import_result=False))

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: import_3d_cad"):
        import_type2_step_ledger_into_hfss(
            hfss=cast(HfssSession, session),
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        )

    assert session.insert_design_calls == ["type2_step_import"]
    assert session.desktop_class.release_calls == [(False, False)]


def test_import_type2_step_ledger_into_hfss_releases_desktop_when_save_project_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(imported_name_batches=[_single_layer_imported_name_batch()]),
        save_project_result=False,
    )

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: save_project"):
        import_type2_step_ledger_into_hfss(
            hfss=cast(HfssSession, session),
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=imported_ledger_path,
        )

    assert session.insert_design_calls == ["type2_step_import"]
    assert session.desktop_class.release_calls == [(False, False)]
    assert not imported_ledger_path.exists()


def test_import_type2_step_ledger_fails_for_plate_stack_terminal_metadata_before_hfss_launch(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    tx_entry = _tx_plate_stack_entry(tmp_path)
    tx_entry["terminal_metadata"] = {"kind": "port"}
    launch_count = 0

    def _factory(_: str) -> HfssSession:
        nonlocal launch_count
        launch_count += 1
        return cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[])))

    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[tx_entry],
    )

    with pytest.raises(ValueError, match=r"terminal_metadata\.kind must be 'stub_port'"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=_factory,
        )

    assert launch_count == 0


def test_import_type2_step_ledger_fails_for_missing_scene_step_before_hfss_launch(tmp_path: Path) -> None:
    scene_step = tmp_path / "missing_type2_scene.step"
    ledger_path = tmp_path / "type2_step_ledger.json"
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    launch_count = 0

    def _factory(_: str) -> HfssSession:
        nonlocal launch_count
        launch_count += 1
        return cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[])))

    with pytest.raises(FileNotFoundError, match=r"scene_step_path does not exist"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=_factory,
        )

    assert launch_count == 0


def test_import_type2_step_ledger_fails_for_missing_required_field(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    del payload["scene_step_path"]
    ledger_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=r"type2_step_ledger is missing required key 'scene_step_path'"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[]))),
        )


def test_import_type2_step_ledger_fails_for_missing_outputs_field(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    del payload["outputs"]
    ledger_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=r"type2_step_ledger is missing required key 'outputs'"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[]))),
        )


def test_import_type2_step_ledger_fails_for_duplicate_object_id(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry(object_id="dup")],
        modeled_objects=[_modeled_entry(object_id="dup")],
    )

    with pytest.raises(ValueError, match=r"duplicate type2 object id in STEP ledger: dup"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[]))),
        )


def test_import_type2_step_ledger_releases_desktop_when_import_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[], import_result=False))

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: import_3d_cad"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )

    assert session.desktop_class.release_calls == [(True, True)]


def test_import_type2_step_ledger_raises_when_save_project_returns_false(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=_single_layer_modeled_objects(tmp_path),
    )
    imported_ledger_path = tmp_path / "aedt" / "type2_imported_ledger.json"
    session = _FakeHfss(
        modeler=_FakeModeler(imported_name_batches=[_single_layer_imported_name_batch()]),
        save_project_result=False,
    )

    with pytest.raises(RuntimeError, match=r"PyAEDT operation returned False: save_project"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=imported_ledger_path,
            hfss_factory=lambda _: cast(HfssSession, session),
        )

    assert session.desktop_class.release_calls == [(True, True)]
    assert session.mesh_module.assign_length_op_calls == []
    assert session.modeler.created_region_name == ""
    assert session.radiation_boundary_calls == []
    assert not imported_ledger_path.exists()


@pytest.mark.parametrize(
    ("batches", "match"),
    [
        ([()], r"STEP import created no new HFSS objects"),
        ([("dup", "dup")], r"STEP import produced duplicate new HFSS object names"),
    ],
)
def test_import_type2_step_ledger_rejects_bad_import_diff(
    tmp_path: Path,
    batches: list[tuple[str, ...]],
    match: str,
) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_non_model_entry()],
        modeled_objects=[_modeled_entry()],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=batches))

    with pytest.raises(RuntimeError, match=match):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=lambda _: cast(HfssSession, session),
        )

    assert session.desktop_class.release_calls == [(True, True)]


def test_import_type2_step_ledger_fails_when_tx_region_member_is_missing(tmp_path: Path) -> None:
    scene_step, ledger_path = _source_paths(tmp_path)
    non_model_entry = _non_model_entry()
    non_model_entry["member_object_ids"] = ("environment", "rx_region_max")
    non_model_entry["member_objects"] = [
        member
        for member in cast(list[dict[str, object]], non_model_entry["member_objects"])
        if cast(str, member["object_id"]) != "tx_region"
    ]
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[non_model_entry],
        modeled_objects=[_modeled_entry()],
    )
    launch_count = 0

    def _factory(_: str) -> HfssSession:
        nonlocal launch_count
        launch_count += 1
        return cast(HfssSession, _FakeHfss(modeler=_FakeModeler(imported_name_batches=[])))

    with pytest.raises(ValueError, match=r"exactly one tx_region member object"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            hfss_factory=_factory,
        )

    assert launch_count == 0
