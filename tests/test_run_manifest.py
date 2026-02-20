from __future__ import annotations

from pathlib import Path

import pytest

import peetsfea.design_manifest_runner as runner


def _write_toml(path: Path, count: int = 8, start: float = 6, end: float = 20, is_integer: bool = True) -> None:
    path.write_text(
        "\n".join(
            [
                'spec_version = "0.1.0"',
                "",
                "[design]",
                'name = "test_design"',
                'units = "mm"',
                "",
                "[backend]",
                'tool = "hfss"',
                "",
                "[parameters.coil1_turns]",
                f"range = [{str(is_integer).lower()}, {start}, {end}, {count}]",
            ]
        ),
        encoding="utf-8",
    )


def test_build_candidates_integer_round_and_dedup() -> None:
    values = runner._build_candidates(is_integer=True, start=0.0, end=1.0, count=5)
    assert values == [0, 1]


def test_build_candidates_float() -> None:
    values = runner._build_candidates(is_integer=False, start=0.0, end=1.0, count=3)
    assert values == [0.0, 0.5, 1.0]


def test_run_creates_manifest_and_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)

    monkeypatch.setattr(runner, "_get_git_commit_and_dirty", lambda _: ("a" * 40, False))
    monkeypatch.chdir(tmp_path)

    config = runner.RunConfig(
        ansys_executable_path="/bin/ansysedt",
        ansys_run_dir="/tmp/aedt",
        toml_path=str(toml_path),
        seed=1,
        backend="hfss",
    )
    first = runner.run(config)
    second = runner.run(config)

    assert first["design_id"] == second["design_id"]
    assert first["selected_parameters"] == second["selected_parameters"]
    assert first["selected_parameters"]["coil1_turns"] == 8

    manifest_file = tmp_path / f"manifest_{first['design_id']}.json"
    assert manifest_file.exists()


def test_run_seed_changes_selection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(runner, "_get_git_commit_and_dirty", lambda _: ("b" * 40, False))
    monkeypatch.chdir(tmp_path)

    m1 = runner.run(
        runner.RunConfig("/bin/ansysedt", "/tmp/aedt", str(toml_path), seed=1, backend="hfss")
    )
    m2 = runner.run(
        runner.RunConfig("/bin/ansysedt", "/tmp/aedt", str(toml_path), seed=2, backend="hfss")
    )
    assert m1["design_id"] != m2["design_id"]


def test_invalid_range_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "bad.toml"
    _write_toml(toml_path, count=0)
    monkeypatch.setattr(runner, "_get_git_commit_and_dirty", lambda _: ("c" * 40, False))

    with pytest.raises(ValueError, match="count"):
        runner.run(runner.RunConfig("/bin/ansysedt", "/tmp/aedt", str(toml_path), seed=1, backend="hfss"))


def test_dirty_git_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml_path = tmp_path / "spec.toml"
    _write_toml(toml_path)
    monkeypatch.setattr(runner, "_get_git_commit_and_dirty", lambda _: ("d" * 40, True))

    with pytest.raises(RuntimeError, match="dirty"):
        runner.run(runner.RunConfig("/bin/ansysedt", "/tmp/aedt", str(toml_path), seed=1, backend="hfss"))
