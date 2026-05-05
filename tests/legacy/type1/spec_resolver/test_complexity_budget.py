from __future__ import annotations

import ast
from pathlib import Path


def _function_metrics(path: Path, function_name: str) -> tuple[int, int]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            end_lineno = getattr(node, "end_lineno", node.lineno)
            line_count = int(end_lineno - node.lineno + 1)

            class _BranchCounter(ast.NodeVisitor):
                def __init__(self) -> None:
                    self.score = 0

                def visit_If(self, node: ast.If) -> None:
                    self.score += 1
                    self.generic_visit(node)

                def visit_For(self, node: ast.For) -> None:
                    self.score += 1
                    self.generic_visit(node)

                def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
                    self.score += 1
                    self.generic_visit(node)

                def visit_While(self, node: ast.While) -> None:
                    self.score += 1
                    self.generic_visit(node)

                def visit_Try(self, node: ast.Try) -> None:
                    self.score += 1
                    self.generic_visit(node)

                def visit_BoolOp(self, node: ast.BoolOp) -> None:
                    self.score += 1
                    self.generic_visit(node)

            counter = _BranchCounter()
            for statement in node.body:
                counter.visit(statement)
            return line_count, counter.score
    raise AssertionError(f"Function not found: {function_name} in {path}")


def test_geometry_entrypoint_complexity_budget() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    path = repo_root / "src" / "peetsfea" / "backend" / "pyaedt" / "geometry" / "build.py"
    lines, branch_score = _function_metrics(path, "build_square_spiral_from_manifest")
    assert lines <= 180, f"build_square_spiral_from_manifest line budget exceeded: {lines}"
    assert branch_score <= 40, f"build_square_spiral_from_manifest branch score budget exceeded: {branch_score}"


def test_finalize_solids_complexity_budget() -> None:
    repo_root = Path(__file__).resolve().parents[4]
    path = repo_root / "src" / "peetsfea" / "backend" / "pyaedt" / "geometry" / "builders" / "build_finalize_ops.py"
    lines, branch_score = _function_metrics(path, "finalize_solids_and_substrates")
    assert lines <= 180, f"finalize_solids_and_substrates line budget exceeded: {lines}"
    assert branch_score <= 40, f"finalize_solids_and_substrates branch score budget exceeded: {branch_score}"
