from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import cast

from peetsfea.type2_step_export import export_type2_step_artifacts

_FORBIDDEN_MEMBER_OBJECT_IDS = {
    "tx_outer_region",
    "tx_outer_actual_region",
    "tx_outer_rect_void_coil",
    "tx_pos_bridge_pcb",
    "tx_pos_bridge_copper",
    "tx_neg_bridge_pcb",
    "tx_neg_bridge_copper",
}
_FORBIDDEN_MEMBER_ROLES = {
    "tx_outer_region",
    "tx_outer_actual_region",
    "tx_outer_single_coil",
    "tx_inner_outer_positive_bridge",
    "tx_inner_outer_negative_bridge",
}
_FORBIDDEN_SCENE_LABEL_PREFIX = "tx_outer_"


def _type2_fixed_spec_path() -> Path:
    return Path(__file__).resolve().parents[2] / "examples" / "type2_fixed.toml"


def test_active_export_omits_tx_outer_modeled_entry_and_keeps_tx_inner_rx(
    tmp_path: Path,
) -> None:
    ledger = export_type2_step_artifacts(
        toml_path=_type2_fixed_spec_path(),
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=17,
    )

    modeled_objects = ledger["modeled_objects"]
    modeled_object_ids = tuple(entry["object_id"] for entry in modeled_objects)
    modeled_roles = tuple(entry["role"] for entry in modeled_objects)

    assert modeled_object_ids == ("tx_inner_rect_void_coil", "rx_rect_void_coil")
    assert modeled_roles == ("tx_inner_single_coil", "rx_single_coil")
    assert "tx_outer_rect_void_coil" not in modeled_object_ids
    assert "tx_outer_single_coil" not in modeled_roles


def test_active_export_omits_tx_outer_actual_region_groups_and_bridge_members(
    tmp_path: Path,
) -> None:
    ledger = export_type2_step_artifacts(
        toml_path=_type2_fixed_spec_path(),
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=17,
    )

    non_model_entry = ledger["non_model_objects"][0]
    member_object_ids = tuple(cast(Sequence[str], non_model_entry["member_object_ids"]))
    member_objects = cast(Sequence[dict[str, object]], non_model_entry["member_objects"])
    member_roles = tuple(cast(str, member["role"]) for member in member_objects)
    expected_exported_groups = tuple(
        body_group
        for modeled_object in ledger["modeled_objects"]
        for body_group in cast(Sequence[dict[str, object]], modeled_object["expected_exported_body_groups"])
    )

    assert _FORBIDDEN_MEMBER_OBJECT_IDS.isdisjoint(member_object_ids)
    assert _FORBIDDEN_MEMBER_ROLES.isdisjoint(member_roles)
    assert "tx_inner_actual_region" in member_object_ids
    assert all(group["group_name"] != "g_ferrite_tx_outer" for group in expected_exported_groups)


def test_active_export_omits_tx_outer_body_and_bridge_scene_labels(
    tmp_path: Path,
) -> None:
    ledger = export_type2_step_artifacts(
        toml_path=_type2_fixed_spec_path(),
        output_dir=tmp_path / "out",
        ledger_path=tmp_path / "out" / "ledger.json",
        seed=17,
    )

    scene_label_candidates = set()
    non_model_entry = ledger["non_model_objects"][0]
    scene_label_candidates.update(cast(Sequence[str], non_model_entry["member_object_ids"]))
    for modeled_object in ledger["modeled_objects"]:
        scene_label_candidates.update(cast(Sequence[str], modeled_object["expected_exported_body_names"]))

    assert _FORBIDDEN_MEMBER_OBJECT_IDS.isdisjoint(scene_label_candidates)
    assert all(
        not label.startswith(_FORBIDDEN_SCENE_LABEL_PREFIX)
        for label in scene_label_candidates
    )
