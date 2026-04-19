from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from peetsfea.aedt.protocols import HfssSession
from peetsfea.backend.pyaedt.type2_step_import_pipeline import import_type2_step_ledger
from peetsfea.type2_step_ledger import ExportedBodyGroup
from tests.backend_em.test_type2_step_import_pipeline import _FakeHfss
from tests.backend_em.test_type2_step_import_pipeline import _FakeModeler
from tests.backend_em.test_type2_step_import_pipeline import _plate_stack_modeled_entry
from tests.backend_em.test_type2_step_import_pipeline import _plate_stack_non_model_entry
from tests.backend_em.test_type2_step_import_pipeline import _plate_stack_terminal_metadata
from tests.backend_em.test_type2_step_import_pipeline import _rx_plate_stack_entry
from tests.backend_em.test_type2_step_import_pipeline import _source_paths
from tests.backend_em.test_type2_step_import_pipeline import _write_ledger


def _tx_array_expected_names(*, branch_count: int) -> list[str]:
    names: list[str] = []
    for index in range(branch_count):
        names.extend(
            (
                f"tx_b{index}_plate_copper",
                f"tx_b{index}_pcb_wall",
                f"tx_b{index}_stack_pet_psa",
                f"tx_b{index}_stack_ferrite",
                f"tx_b{index}_stack_air",
                f"tx_b{index}_pcb_coil",
            )
        )
    for index in range(branch_count - 1):
        names.extend((f"tx_array_input_sheet_s{index}", f"tx_array_output_sheet_s{index}"))
    return names


def _tx_array_expected_groups(*, branch_count: int) -> list[ExportedBodyGroup]:
    ferrite_names = [
        name
        for name in _tx_array_expected_names(branch_count=branch_count)
        if name.endswith("_stack_pet_psa") or name.endswith("_stack_ferrite") or name.endswith("_stack_air")
    ]
    return [
        {
            "group_name": "g_copper_tx",
            "member_body_names": tuple(
                name
                for name in _tx_array_expected_names(branch_count=branch_count)
                if name.endswith("_plate_copper") or name.startswith("tx_array_")
            ),
        },
        {"group_name": "g_ferrite_tx", "member_body_names": tuple(ferrite_names)},
    ]


def _tx_array_connector_vertices_by_name(*, branch_count: int) -> dict[str, list[list[float]]]:
    vertices_by_name: dict[str, list[list[float]]] = {}
    for index in range(branch_count - 1):
        x0 = float(index)
        x1 = float(index + 1)
        vertices_by_name[f"tx_array_input_sheet_s{index}"] = [
            [x0, -145.0, 10.0],
            [x1, -145.0, 10.0],
            [x1, -145.0, 20.0],
            [x0, -145.0, 20.0],
        ]
        vertices_by_name[f"tx_array_output_sheet_s{index}"] = [
            [x0, -145.0, 40.0],
            [x1, -145.0, 40.0],
            [x1, -145.0, 50.0],
            [x0, -145.0, 50.0],
        ]
    return vertices_by_name


def _tx_array_terminal_metadata(*, branch_count: int) -> dict[str, object]:
    terminal = _plate_stack_terminal_metadata(
        owner_origin_y=-140.0,
        owner_size_y=280.0,
        owner_origin_z=0.0,
        owner_size_z=90.0,
        copper_thickness_mm=0.035,
        prefix="tx",
    )
    terminal["input_stub_body_name"] = "tx_array_input_sheet_s0"
    terminal["output_stub_body_name"] = "tx_array_output_sheet_s0"
    raw_vertices = cast(list[list[float]], terminal["port_sheet_vertices_xyz"])
    raw_vertices[1][0] = 80.0 + float(branch_count)
    raw_vertices[2][0] = 80.0 + float(branch_count)
    return terminal


def _tx_array_entry(
    tmp_path: Path,
    *,
    branch_count: int,
    size_xyz: tuple[float, float, float] = (85.0, 285.0, 90.0),
) -> dict[str, object]:
    entry = _plate_stack_modeled_entry(
        object_id="tx_plate_stack",
        role="tx_plate_stack",
        plane="YZ",
        placement_owner_id="tx_region",
        origin_xyz=(0.0, -145.0, 0.0),
        size_xyz=size_xyz,
        source_metadata_path=str(tmp_path / "tx_plate_stack.metadata.json"),
        expected_names=_tx_array_expected_names(branch_count=branch_count),
        expected_groups=_tx_array_expected_groups(branch_count=branch_count),
        pcb_layer_positions_mm=[0.035, 5.3],
        copper_layer_positions_mm=[0.0, 6.865],
        terminal_metadata=_tx_array_terminal_metadata(branch_count=branch_count),
    )
    canonical_coordinates = cast(dict[str, object], entry["canonical_coordinates"])
    canonical_coordinates["connector_sheet_vertices_xyz_by_name"] = _tx_array_connector_vertices_by_name(
        branch_count=branch_count
    )
    return entry


def _array_imported_name_batch(*, branch_count: int) -> tuple[str, ...]:
    return (
        "environment",
        "tx_region",
        "rx_region_max",
        *[name for name in _tx_array_expected_names(branch_count=branch_count) if not name.startswith("tx_array_")],
        "rx_plate_copper",
        "rx_pcb_wall",
        "rx_stack_pet_psa",
        "rx_stack_ferrite",
        "rx_stack_air",
        "rx_pcb_coil",
    )


def test_import_type2_step_ledger_accepts_tx_plate_stack_array_names(tmp_path: Path) -> None:
    branch_count = 3
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=[_tx_array_entry(tmp_path, branch_count=branch_count), _rx_plate_stack_entry(tmp_path)],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_array_imported_name_batch(branch_count=branch_count)]))

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
        imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    tx_entry = next(entry for entry in result["modeled_objects"] if entry["object_id"] == "tx_plate_stack")
    tx_names = cast(list[str], tx_entry["imported_object_names"])
    assert "tx_b0_plate_copper" in tx_names
    assert "tx_array_input_sheet_s0" in tx_names
    assert "tx_b0_pcb_wall" in tx_names
    assert "tx_b2_stack_ferrite" in tx_names
    assert "tx_pcb_wall" not in tx_names


def test_import_type2_step_ledger_accepts_tx_plate_stack_array_x_overflow(tmp_path: Path) -> None:
    branch_count = 3
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=[
            _tx_array_entry(tmp_path, branch_count=branch_count, size_xyz=(210.0, 285.0, 90.0)),
            _rx_plate_stack_entry(tmp_path),
        ],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_array_imported_name_batch(branch_count=branch_count)]))

    result = import_type2_step_ledger(
        step_ledger_path=ledger_path,
        output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
        imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
        design_name="fake_type2_import",
        hfss_factory=lambda _: cast(HfssSession, session),
    )

    tx_entry = next(entry for entry in result["modeled_objects"] if entry["object_id"] == "tx_plate_stack")
    tx_names = cast(list[str], tx_entry["imported_object_names"])
    assert tx_entry is not None
    assert "tx_b0_plate_copper" in tx_names


def test_import_type2_step_ledger_rejects_tx_plate_stack_array_z_overflow(tmp_path: Path) -> None:
    branch_count = 3
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=[
            _tx_array_entry(tmp_path, branch_count=branch_count, size_xyz=(85.0, 285.0, 91.0)),
            _rx_plate_stack_entry(tmp_path),
        ],
    )
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[_array_imported_name_batch(branch_count=branch_count)]))

    with pytest.raises(ValueError, match=r"outer bounds must fit inside tx_region"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )


def test_import_type2_step_ledger_rejects_tx_plate_stack_array_solid_leakage(tmp_path: Path) -> None:
    branch_count = 3
    scene_step, ledger_path = _source_paths(tmp_path)
    _write_ledger(
        ledger_path,
        scene_step_path=scene_step,
        non_model_objects=[_plate_stack_non_model_entry()],
        modeled_objects=[_tx_array_entry(tmp_path, branch_count=branch_count), _rx_plate_stack_entry(tmp_path)],
    )
    imported_names = list(_array_imported_name_batch(branch_count=branch_count))
    imported_names.remove("tx_b1_stack_pet_psa")
    imported_names.append("SOLID_777")
    session = _FakeHfss(modeler=_FakeModeler(imported_name_batches=[tuple(imported_names)]))

    with pytest.raises(ValueError, match=r"SOLID"):
        import_type2_step_ledger(
            step_ledger_path=ledger_path,
            output_aedt_path=tmp_path / "aedt" / "type2_import.aedt",
            imported_ledger_path=tmp_path / "aedt" / "type2_imported_ledger.json",
            design_name="fake_type2_import",
            hfss_factory=lambda _: cast(HfssSession, session),
        )
