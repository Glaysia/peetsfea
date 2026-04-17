from __future__ import annotations

import json
from pathlib import Path


def test_launch_json_has_dedicated_sample_build_debug_entry() -> None:
    workspace_root = Path(__file__).resolve().parents[4]
    launch = json.loads((workspace_root / ".vscode" / "launch.json").read_text(encoding="utf-8"))
    configurations = launch["configurations"]

    assert len(configurations) == 2
    config = next(entry for entry in configurations if entry["name"] == "legacy-type1 Run entry/sample_build.py from run/")
    assert config["program"] == "${workspaceFolder}/entry/legacy/type1/sample_build.py"
    assert config["cwd"] == "${workspaceFolder}/run"
    assert config["preLaunchTask"] == "prepare-build-debug"
    assert config["env"]["PEETSFEA_DEBUG"] == "1"
    assert "PEETSFEA_BREAK_BEFORE_RELEASE" not in config["env"]


def test_tasks_json_only_keeps_launch_linked_prepare_tasks() -> None:
    workspace_root = Path(__file__).resolve().parents[4]
    tasks = json.loads((workspace_root / ".vscode" / "tasks.json").read_text(encoding="utf-8"))
    labels = [entry["label"] for entry in tasks["tasks"]]
    assert "install-dev-editable" in labels
    assert "clean-run-aedt" in labels
    assert "prepare-build-debug" in labels
    assert "clean-run-toml" not in labels
    assert "prepare-sample-debug" not in labels
    assert "prepare-sample-build-debug" not in labels
    assert "legacy-type1-run-sample-debug" in labels
    assert "run-type2-import-debug" in labels

    sample_task = next(entry for entry in tasks["tasks"] if entry["label"] == "legacy-type1-run-sample-debug")
    assert (
        sample_task["command"]
        == "mkdir -p ${workspaceFolder}/run/toml && find ${workspaceFolder}/run/toml -mindepth 1 -maxdepth 1 -exec rm -rf {} + && ${workspaceFolder}/.venv/bin/python ../entry/legacy/type1/sample.py"
    )
    assert sample_task["options"]["cwd"] == "${workspaceFolder}/run"
    assert sample_task["dependsOn"] == ["install-dev-editable"]
