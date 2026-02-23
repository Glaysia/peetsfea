from __future__ import annotations

import re

import pytest

from peetsfea.identity.hashing import compose_design_id, compute_design_unique_hash, compute_toml_space_hash
from peetsfea.types.manifest import SelectedParameters


def _selected_parameters() -> SelectedParameters:
    return {
        "pcb_count": 1,
        "turns": 6,
        "outer": 40.0,
        "trace": 1.0,
        "gap": 0.5,
        "profile_id": "p1",
        "via_diameter": 0.6,
        "pcb_thickness": 1.6,
        "cu_thickness": 0.035,
        "fr4_er": 4.4,
    }


def test_compute_toml_space_hash_uses_toml_hash_prefix() -> None:
    toml_hash = "a" * 64
    assert compute_toml_space_hash(toml_hash) == "aaaaaaaa"


def test_compute_design_unique_hash_is_deterministic() -> None:
    selected = _selected_parameters()
    first = compute_design_unique_hash("b" * 64, "c" * 40, 7, selected)
    second = compute_design_unique_hash("b" * 64, "c" * 40, 7, selected)
    assert first == second
    assert re.fullmatch(r"[0-9a-f]{8}", first) is not None


def test_compose_design_id_format() -> None:
    design_id = compose_design_id("deadbeef", "cafebabe", -3)
    assert design_id == "deadbeef_cafebabe_-3"
    assert re.fullmatch(r"[0-9a-f]{8}_[0-9a-f]{8}_-?[0-9]+", design_id) is not None


def test_compute_toml_space_hash_rejects_bad_toml_hash() -> None:
    with pytest.raises(ValueError, match="toml_hash"):
        compute_toml_space_hash("A" * 64)

    with pytest.raises(ValueError, match="toml_hash"):
        compute_toml_space_hash("a" * 63)
