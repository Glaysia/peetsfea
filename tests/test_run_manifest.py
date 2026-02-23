from __future__ import annotations

from pathlib import Path
import re

import pytest

import peetsfea.pipeline.run_design as runner


def _write_toml(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                'spec_version = "0.1.3"',
                "",
                "[design]",
                'units = "mm"',
                "",
                "[backend]",
                'tool = "hfss"',
                "",
                "[parameters.pcb_count]",
                "range = [true, 1, 1, 1]",
                "",
                "[parameters.turns]",
                "range = [true, 4, 8, 5]",
                "",
                "[parameters.outer]",
                "range = [false, 40.0, 52.0, 4]",
                "",
                "[parameters.trace]",
                "range = [false, 0.6, 1.2, 4]",
                "",
                "[parameters.gap]",
                "range = [false, 0.2, 0.6, 4]",
                "",
                "[parameters.via_diameter]",
                "range = [false, 0.3, 0.7, 4]",
                "",
                "[parameters.pcb_thickness]",
                "range = [false, 1.6, 1.6, 1]",
                "",
                "[parameters.cu_thickness]",
                "range = [false, 0.035, 0.035, 1]",
                "",
                "[parameters.fr4_er]",
                "range = [false, 4.4, 4.4, 1]",
            ]
        ),
        encoding="utf-8",
    )


def test_build_candidates_integer_round_and_dedup() -> None:
    values = runner._build_candidates(is_integer=True, start=0.0, end=1.0, count=5)
    assert list(values) == [0, 1]


def test_build_candidates_float() -> None:
    values = runner._build_candidates(is_integer=False, start=0.0, end=1.0, count=3)
    assert list(values) == [0.0, 0.5, 1.0]


def test_run_creates_manifest_and_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)

    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("a" * 40))
    monkeypatch.chdir(tmp_path)

    config = runner.RunConfig(
        ansys_executable_path="/bin/ansysedt",
        ansys_run_dir=str(tmp_path / "run"),
        toml_path=str(toml_path),
        seed=1,
        backend="hfss",
    )
    first = runner.run(config)
    second = runner.run(config)

    assert first["design_id"] == second["design_id"]
    assert first["selected_parameters"] == second["selected_parameters"]
    assert set(first["selected_parameters"].keys()) == {
        "pcb_count",
        "turns",
        "outer",
        "trace",
        "gap",
        "via_diameter",
        "pcb_thickness",
        "cu_thickness",
        "fr4_er",
    }
    assert first["selected_parameters"]["pcb_count"] == 1
    assert first["selected_parameters"]["pcb_thickness"] == 1.6
    assert first["selected_parameters"]["cu_thickness"] == 0.035
    assert first["inputs"]["non_graphical"] is True
    assert first["inputs"]["close_on_exit"] is True
    assert first["design_id"].split("_")[0] == first["design_unique_hash"]
    assert first["design_id"].split("_")[1] == first["toml_space_hash"]
    assert re.fullmatch(r"[0-9a-f]{8}_[0-9a-f]{8}_-?[0-9]+", first["design_id"]) is not None
    assert first["manifest_path"].endswith(f"manifest_{first['design_id']}.json")

    manifest_file = tmp_path / "run" / f"manifest_{first['design_id']}.json"
    assert manifest_file.exists()


def test_run_seed_changes_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("b" * 40))
    monkeypatch.chdir(tmp_path)

    m1 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
    m2 = runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=2, backend="hfss"))
    assert m1["design_id"] != m2["design_id"]


def test_invalid_range_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad.toml"
    toml_path.write_text(
        "\n".join(
            [
                'spec_version = "0.1.3"',
                "[design]",
                'units = "mm"',
                "[backend]",
                'tool = "hfss"',
                "[parameters.pcb_count]",
                "range = [true, 1, 1, 1]",
                "[parameters.turns]",
                "range = [true, 6, 10, 0]",
                "[parameters.outer]",
                "range = [false, 40.0, 50.0, 3]",
                "[parameters.trace]",
                "range = [false, 0.5, 1.0, 3]",
                "[parameters.gap]",
                "range = [false, 0.2, 0.3, 3]",
                "[parameters.via_diameter]",
                "range = [false, 0.4, 0.4, 1]",
                "[parameters.pcb_thickness]",
                "range = [false, 1.6, 1.6, 1]",
                "[parameters.cu_thickness]",
                "range = [false, 0.035, 0.035, 1]",
                "[parameters.fr4_er]",
                "range = [false, 4.4, 4.4, 1]",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("c" * 40))

    with pytest.raises(ValueError, match="count"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_rejects_removed_parameter_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "legacy.toml"
    _write_toml(toml_path)
    toml_path.write_text(toml_path.read_text(encoding="utf-8") + "\n[parameters.bridge_width]\nrange = [false, 1.0, 1.0, 1]\n", encoding="utf-8")
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("d" * 40))

    with pytest.raises(ValueError, match="Unsupported parameter keys"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_geometry_constraint_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad_geom.toml"
    toml_path.write_text(
        "\n".join(
            [
                'spec_version = "0.1.3"',
                "[design]",
                'units = "mm"',
                "[backend]",
                'tool = "hfss"',
                "[parameters.pcb_count]",
                "range = [true, 1, 1, 1]",
                "[parameters.turns]",
                "range = [true, 12, 12, 1]",
                "[parameters.outer]",
                "range = [false, 20.0, 20.0, 1]",
                "[parameters.trace]",
                "range = [false, 1.5, 1.5, 1]",
                "[parameters.gap]",
                "range = [false, 0.5, 0.5, 1]",
                "[parameters.via_diameter]",
                "range = [false, 0.6, 0.6, 1]",
                "[parameters.pcb_thickness]",
                "range = [false, 1.6, 1.6, 1]",
                "[parameters.cu_thickness]",
                "range = [false, 0.035, 0.035, 1]",
                "[parameters.fr4_er]",
                "range = [false, 4.4, 4.4, 1]",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "get_git_commit", lambda _: ("e" * 40))

    with pytest.raises(ValueError, match="inner width"):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))


def test_git_commit_lookup_failure_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(
        runner,
        "get_git_commit",
        lambda _: (_ for _ in ()).throw(RuntimeError("git commit lookup failed")),
    )

    with pytest.raises(RuntimeError):
        runner.run(runner.RunConfig("/bin/ansysedt", str(tmp_path), str(toml_path), seed=1, backend="hfss"))
