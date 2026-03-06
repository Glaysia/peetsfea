from __future__ import annotations

from pathlib import Path
import re

import pytest

import peetsfea.pipeline.run_design as runner
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.spec.resolver import SelectionConstraintError, resolve_selection
from tests.fixtures.type1_spec import write_type1_toml


def test_build_candidates_integer_round_and_dedup() -> None:
    values = runner._build_candidates(is_integer=True, start=0.0, end=1.0, count=5)
    assert list(values) == [0, 1]


def test_build_candidates_float() -> None:
    values = runner._build_candidates(is_integer=False, start=0.0, end=1.0, count=3)
    assert list(values) == [0.0, 0.5, 1.0]


def test_run_creates_manifest_and_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("a" * 40))

    config = runner.RunConfig("/bin/ansysedt", str(tmp_path / "run"), str(toml_path), seed=7, backend="hfss")
    first_result = runner.run(config)
    second_result = runner.run(config)
    first = first_result["manifest"]
    second = second_result["manifest"]

    assert first["design_id"] == second["design_id"]
    assert first["selected_parameters"] == second["selected_parameters"]
    assert first["selected_group_geometry"] == second["selected_group_geometry"]
    assert first["selected_coil_groups"] == second["selected_coil_groups"]
    assert first["selected_pcbs"] == second["selected_pcbs"]
    assert first_result["source_toml_bytes"] == second_result["source_toml_bytes"]
    assert first_result["repro_snapshot"]["toml_bytes"] == second_result["repro_snapshot"]["toml_bytes"]
    assert first_result["dataset_snapshot"]["toml_bytes"] == second_result["dataset_snapshot"]["toml_bytes"]

    assert first["selected_parameters"]["tx_vertical_outer_x"] == first["selected_parameters"]["tx_dd_outer_x"]
    pcbs_by_id = {pcb["id"]: pcb for pcb in first["selected_pcbs"]}
    tx_z_delta = float(pcbs_by_id["tx_main_1"]["position"][2]) - float(pcbs_by_id["tx_main_0"]["position"][2])
    assert tx_z_delta in (3.0, 4.75, 6.5, 8.25, 10.0)
    assert tx_z_delta >= 3.0
    assert first["retry_attempt"] >= 0
    assert first["retry_count"] == first["retry_attempt"]
    assert len(first["selected_group_geometry"]) == 3
    assert {entry["kind"] for entry in first["selected_group_geometry"]} == {"tx_dd", "tx_vertical", "rx_dd"}
    assert first["manifest_path"] is None
    assert re.fullmatch(r"-?[0-9]{6,}_[0-9a-f]{4}_[0-9a-f]{4}_[0-9]+", first["design_id"]) is not None


def test_seed_changes_group_geometry_and_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("b" * 40))

    m1 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))["manifest"]
    m2 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=2, backend="hfss"))["manifest"]

    assert m1["design_id"] != m2["design_id"]
    assert m1["selected_group_geometry"] != m2["selected_group_geometry"]


def test_retry_attempt_advances_until_constraint_satisfied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "retry.toml"
    write_type1_toml(toml_path, outer_x=140.0)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "[coil_shape.tx_dd.outer_x]\nrange = [false, 140.0, 140.0, 1]",
        "[coil_shape.tx_dd.outer_x]\nrange = [false, 120.0, 320.0, 2]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("2" * 40))

    manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))["manifest"]
    assert manifest["retry_attempt"] > 0
    assert manifest["retry_count"] == manifest["retry_attempt"]


def test_feasibility_constraint_allows_retry_to_find_valid_case(tmp_path: Path) -> None:
    toml_path = tmp_path / "feasibility_retry.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 20, 20]",
        "[coil_groups_params.tx_vertical.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
        "[coil_groups_params.tx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 20, 20]",
        "[coil_groups_params.rx_dd.turn_count_max]\nrange = [true, 1, 1, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.rx_dd.band_ratio]\nrange = [false, 0.2, 0.2, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.rx_dd.metal_ratio]\nrange = [false, 0.5, 0.5, 1]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.1, 0.9, 81]",
        "[coil_groups_params.tx_vertical.band_ratio]\nrange = [false, 0.2, 0.9, 2]",
    )
    raw = raw.replace(
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.15, 0.85, 71]",
        "[coil_groups_params.tx_vertical.metal_ratio]\nrange = [false, 0.85, 0.85, 1]",
    )
    raw = raw.replace("count_range = [true, 1, 6, 6]", "count_range = [true, 1, 1, 1]")
    raw += (
        "\n[[constraints.rules]]\n"
        'id = "tx_vertical_feasible_turns_for_active_group"\n'
        'kind = "comparison"\n'
        'message = "tx_vertical active group must support >=1 feasible turn in capped vertical zone"\n'
        'lhs = { func = "feasible_turns(tx_vertical,outer_x,outer_y,tx_region_vertical_z_mm)" }\n'
        'op = ">="\n'
        'rhs = { func = "active_group(tx_vertical)" }\n'
    )
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(SelectionConstraintError):
        resolve_selection(spec=spec, seed=2, attempt=0)

    selected, _, groups, geometries, _ = resolve_selection(spec=spec, seed=2, attempt=1)
    groups_by_kind = {group["kind"]: group for group in groups}
    assert int(groups_by_kind["tx_vertical"]["selected_count"]) == 1
    geom_by_kind = {geom["kind"]: geom for geom in geometries}
    assert float(geom_by_kind["tx_vertical"]["band_ratio"]) == pytest.approx(0.2)
    assert float(selected["tx_region_vertical_z_mm"]) > 0.0


def test_repro_mode_sampled_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "sampled.toml"
    write_type1_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("7" * 40))
    manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=3, backend="hfss"))["manifest"]
    assert manifest["repro_mode"] == "sampled_toml"


def test_repro_mode_frozen_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "frozen.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = re.sub(
        r"range = \[(true|false), ([^,]+), [^,]+, [0-9]+\]",
        lambda m: f"range = [{m.group(1)}, {m.group(2)}, {m.group(2)}, 1]",
        raw,
    )
    raw = raw.replace(
        "[coil_shape.tx_vertical.outer_x]\nrange = [false, -1, -1, 1]",
        "[coil_shape.tx_vertical.outer_x]\nrange = [false, -1, -1, -1]",
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("8" * 40))
    manifest = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=3, backend="hfss"))["manifest"]
    assert manifest["repro_mode"] == "frozen_toml"


def test_determinism_with_pcb_normalization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "determinism_with_normalization.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw = raw.replace(
        "present = [true, 0, 0, 1]",
        "present = [true, 0, 1, 2]",
        4,
    )
    raw = raw.replace(
        "mounts = []",
        '[[pcbs.mounts]]\nkind = "tx_vertical"\nselector_mode = "all"',
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("d" * 40))

    with pytest.warns(UserWarning):
        first = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=17, backend="hfss"))["manifest"]
    with pytest.warns(UserWarning):
        second = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=17, backend="hfss"))["manifest"]

    assert first["design_id"] == second["design_id"]
    assert first["selected_pcbs"] == second["selected_pcbs"]
