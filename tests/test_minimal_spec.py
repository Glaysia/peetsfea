from __future__ import annotations

from pathlib import Path

import pytest

from peetsfea.minimal_spec import SCHEMA_ID, SPEC_VERSION, load_minimal_spec


def _write_spec(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "spec.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _valid_text() -> str:
    return f"""
spec_version = "{SPEC_VERSION}"
schema_id = "{SCHEMA_ID}"

[design]
units = "mm"

[[non_model_objects]]
id = "air_context"
kind = "air_context"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [-100.0, -75.0, -25.0]
size_xyz = [200.0, 150.0, 50.0]
"""


def test_load_minimal_spec_accepts_non_model_only_contract(tmp_path: Path) -> None:
    spec = load_minimal_spec(_write_spec(tmp_path, _valid_text()))

    assert spec.units == "mm"
    assert len(spec.non_model_objects) == 1
    non_model = spec.non_model_objects[0]
    assert non_model.object_id == "air_context"
    assert non_model.origin_xyz == (-100.0, -75.0, -25.0)
    assert non_model.size_xyz == (200.0, 150.0, 50.0)


@pytest.mark.parametrize("section", ["backend", "simulation", "outputs", "modeled_objects", "constraints"])
def test_load_minimal_spec_rejects_old_geometry_contract_sections(tmp_path: Path, section: str) -> None:
    if section in {"modeled_objects", "constraints"}:
        suffix = f"\n[[{section}]]\nid = \"old\"\n"
    else:
        suffix = f"\n[{section}]\nold = true\n"
    path = _write_spec(tmp_path, _valid_text() + suffix)

    with pytest.raises(ValueError, match="removed from the 0.3.0 minimal contract"):
        load_minimal_spec(path)


def test_load_minimal_spec_requires_positive_non_model_size(tmp_path: Path) -> None:
    path = _write_spec(tmp_path, _valid_text().replace("size_xyz = [200.0, 150.0, 50.0]", "size_xyz = [200.0, 0.0, 50.0]"))

    with pytest.raises(ValueError, match=r"size_xyz\[1\] must be > 0"):
        load_minimal_spec(path)
