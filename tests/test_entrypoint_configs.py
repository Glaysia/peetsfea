from __future__ import annotations

import json
from pathlib import Path


def test_launch_json_has_multi_sample_build_and_multi_build_debug_entries() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    launch = json.loads((workspace_root / ".vscode" / "launch.json").read_text(encoding="utf-8"))
    configurations = launch["configurations"]
    names = [entry["name"] for entry in configurations]
    programs = [entry["program"] for entry in configurations]
    assert "Run entry/multi_sample.py from run/" in names
    assert "Run entry/build.py from run/" in names
    assert "Run entry/multi_build.py from run/" in names
    assert "Run entry/build_one.py from run/" in names
    assert "Run entry/sample_one_build.py from run/" in names
    assert "${workspaceFolder}/entry/multi_sample.py" in programs
    assert "${workspaceFolder}/entry/build.py" in programs
    assert "${workspaceFolder}/entry/multi_build.py" in programs
    assert "${workspaceFolder}/entry/build_one.py" in programs
    assert "${workspaceFolder}/entry/sample_one_build.py" in programs
    assert "Run sample.py from run/" not in names


def test_tasks_json_has_separate_sample_and_build_prepare_tasks() -> None:
    workspace_root = Path(__file__).resolve().parents[1]
    tasks = json.loads((workspace_root / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
    labels = [entry["label"] for entry in tasks["tasks"]]
    assert "clean-run-toml" in labels
    assert "clean-run-aedt" in labels
    assert "prepare-sample-debug" in labels
    assert "prepare-build-debug" in labels
    assert "prepare-sample-build-debug" in labels
