from __future__ import annotations

import ast
from pathlib import Path

from peetsfea.backend.pyaedt.geometry.builders.finalize_types import FinalizeArtifacts, FinalizePlan
from peetsfea.backend.pyaedt.geometry.builders.txdd_types import TxDdBuildRequest, TxDdRealization
from peetsfea.backend.pyaedt.geometry.rules.placement_types import PlacementKernelInput, PlacementKernelOutput


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _assert_no_aedt_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith("peetsfea.aedt")
                assert not alias.name.startswith("ansys.aedt")
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not module.startswith("peetsfea.aedt")
            assert not module.startswith("ansys.aedt")


def test_target_facades_stay_small_after_refactor() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assert _line_count(repo_root / "src/peetsfea/backend/pyaedt/geometry/rules/placement_rules.py") <= 200
    assert _line_count(repo_root / "src/peetsfea/backend/pyaedt/geometry/builders/group_builder_tx_dd_impl.py") <= 80
    assert _line_count(repo_root / "src/peetsfea/backend/pyaedt/geometry/builders/build_finalize_ops.py") <= 300


def test_pure_placement_kernel_modules_have_no_aedt_dependency() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    _assert_no_aedt_imports(repo_root / "src/peetsfea/backend/pyaedt/geometry/rules/placement_geometry.py")
    _assert_no_aedt_imports(repo_root / "src/peetsfea/backend/pyaedt/geometry/rules/placement_projection.py")
    _assert_no_aedt_imports(repo_root / "src/peetsfea/backend/pyaedt/geometry/rules/placement_txdd.py")


def test_new_refactor_dataclasses_exist() -> None:
    assert PlacementKernelInput.__name__ == "PlacementKernelInput"
    assert PlacementKernelOutput.__name__ == "PlacementKernelOutput"
    assert TxDdBuildRequest.__name__ == "TxDdBuildRequest"
    assert TxDdRealization.__name__ == "TxDdRealization"
    assert FinalizePlan.__name__ == "FinalizePlan"
    assert FinalizeArtifacts.__name__ == "FinalizeArtifacts"
