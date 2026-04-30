from __future__ import annotations

import argparse
from collections.abc import Callable
from shutil import get_terminal_size
from time import perf_counter
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.console_log import info
from peetsfea.type2_sampled_skip import Type2SampleSkippedEntry
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_sampled import (
    Type2SampleManifestEntry,
    Type2SampleManifestDocument,
    build_type2_sample_manifest_config,
    build_type2_sample_manifest_document,
    generate_sample_manifest_attempts,
    write_type2_sample_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2_sweep.toml"
OUTPUT_DIR = REPO_ROOT / "run" / "sampled" / "type2"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
SEED_FIRST = 0
SEED_N = 12
SAMPLER_N = 12
AEDT_BUILDER_N = 6
MAKE_STEP_ON_SAMPLE = False

_Exporter = Callable[..., object]
_STATUS_PREFIX = "PeetsFEA INFO: "
_STATUS_BAR_MAX_WIDTH = 30
_STATUS_BAR_MIN_WIDTH = 6

class _SampleStatusLine:
    def __init__(self) -> None:
        self._tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        self._active = False
        self._rendered_line = ""
        self._last_completed = 0
        self._last_total = 0
        self._last_detail = ""

    def log(self, message: str) -> None:
        should_restore = self._tty and self._last_total > 0
        self.clear()
        info(message)
        if should_restore:
            self._render(completed=self._last_completed, total=self._last_total, detail=self._last_detail)

    def show_waiting(self, *, total: int) -> None:
        self._render(completed=0, total=total, detail="waiting")

    def update(self, *, completed: int, total: int, entry: Type2SampleManifestEntry) -> None:
        detail = f"last_idx={entry['sample_index']} last_seed={entry['seed']}"
        self._render(completed=completed, total=total, detail=detail)

    def clear(self) -> None:
        if not self._active:
            return
        columns = _terminal_status_columns()
        sys.stdout.write("\r")
        sys.stdout.write(" " * columns)
        sys.stdout.write("\r")
        sys.stdout.flush()
        self._active = False
        self._rendered_line = ""

    def finish(self) -> None:
        if not self._active:
            return
        sys.stdout.write("\n")
        sys.stdout.flush()
        self._active = False
        self._rendered_line = ""

    def _render(self, *, completed: int, total: int, detail: str) -> None:
        assert total > 0
        self._last_completed = completed
        self._last_total = total
        self._last_detail = detail
        ratio = completed / total
        percent = ratio * 100.0
        bar_width = 30
        filled = int(ratio * bar_width)
        if completed == total:
            filled = bar_width
        bar = "#" * filled + "-" * (bar_width - filled)
        message = f"[sample] status [{bar}] {percent:6.2f}% {completed}/{total} {detail}"
        if not self._tty:
            info(message)
            return
        rendered_line = _interactive_status_line(
            completed=completed,
            total=total,
            percent=percent,
            detail=detail,
        )
        padded_line = rendered_line
        previous_width = min(len(self._rendered_line), _terminal_status_columns())
        if previous_width > len(rendered_line):
            padded_line = rendered_line + (" " * (previous_width - len(rendered_line)))
        sys.stdout.write(f"\r{padded_line}")
        sys.stdout.flush()
        self._active = True
        self._rendered_line = rendered_line


def _terminal_status_columns() -> int:
    columns = get_terminal_size().columns
    if columns <= 1:
        return 1
    return columns - 1


def _interactive_status_line(
    *,
    completed: int,
    total: int,
    percent: float,
    detail: str,
) -> str:
    columns = _terminal_status_columns()
    suffix = f"] {percent:6.2f}% {completed}/{total} {detail}"
    fixed_width = len(_STATUS_PREFIX) + len("[sample] status [") + len(suffix)
    bar_width = _STATUS_BAR_MAX_WIDTH
    if fixed_width + bar_width > columns:
        bar_width = columns - fixed_width
    if bar_width < _STATUS_BAR_MIN_WIDTH:
        bar_width = _STATUS_BAR_MIN_WIDTH
    ratio = completed / total
    filled = int(ratio * bar_width)
    if completed == total:
        filled = bar_width
    bar = "#" * filled + "-" * (bar_width - filled)
    rendered_line = f"{_STATUS_PREFIX}[sample] status [{bar}{suffix}"
    if len(rendered_line) <= columns:
        return rendered_line
    return rendered_line[:columns]


def _report_sample_progress(
    status_line: _SampleStatusLine,
    completed: int,
    total: int,
    entry: Type2SampleManifestEntry,
) -> None:
    status_line.log(
        f"[sample] progress {completed}/{total} "
        f"idx={entry['sample_index']} seed={entry['seed']} design_id={entry['design_id']}"
    )
    status_line.update(completed=completed, total=total, entry=entry)


def _report_sample_step_stage(
    status_line: _SampleStatusLine,
    phase: str,
    entry: Type2SampleManifestEntry,
) -> None:
    if phase == "start":
        status_line.log(
            f"[sample] step start idx={entry['sample_index']} "
            f"seed={entry['seed']} design_id={entry['design_id']}"
        )
        return
    if phase == "done":
        status_line.log(
            f"[sample] step done idx={entry['sample_index']} "
            f"seed={entry['seed']} design_id={entry['design_id']}"
        )
        return
    status_line.log(
        f"[sample] step phase={phase} idx={entry['sample_index']} "
        f"seed={entry['seed']} design_id={entry['design_id']}"
    )


def _report_sample_skip(status_line: _SampleStatusLine, skip: Type2SampleSkippedEntry) -> None:
    if "sample_index" not in skip:
        raise ValueError("type2 sample skipped entry is missing required key 'sample_index'")
    if "seed" not in skip:
        raise ValueError("type2 sample skipped entry is missing required key 'seed'")
    if "phase" not in skip:
        raise ValueError("type2 sample skipped entry is missing required key 'phase'")
    if "error_type" not in skip:
        raise ValueError("type2 sample skipped entry is missing required key 'error_type'")
    if "error_message" not in skip:
        raise ValueError("type2 sample skipped entry is missing required key 'error_message'")
    sample_index = skip["sample_index"]
    seed = skip["seed"]
    phase = skip["phase"]
    error_type = skip["error_type"]
    error_message = skip["error_message"]
    if isinstance(sample_index, bool) or not isinstance(sample_index, int):
        raise TypeError("skipped_entry.sample_index must be int")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("skipped_entry.seed must be int")
    if not isinstance(phase, str):
        raise TypeError("skipped_entry.phase must be str")
    if not isinstance(error_type, str):
        raise TypeError("skipped_entry.error_type must be str")
    if not isinstance(error_message, str):
        raise TypeError("skipped_entry.error_message must be str")
    status_line.log(
        f"[sample] skip idx={sample_index} seed={seed} phase={phase} "
        f"error={error_type}: {error_message}"
    )


def sample_type2(
    *,
    source_toml_path: Path = SOURCE_TOML_PATH,
    output_dir: Path = OUTPUT_DIR,
    manifest_path: Path = MANIFEST_PATH,
    seed_first: int = SEED_FIRST,
    seed_n: int = SEED_N,
    sampler_n: int = SAMPLER_N,
    aedt_builder_n: int = AEDT_BUILDER_N,
    make_step_on_sample: bool = MAKE_STEP_ON_SAMPLE,
    exporter: _Exporter = export_type2_step_artifacts,
) -> Type2SampleManifestDocument:
    started_at = perf_counter()
    status_line = _SampleStatusLine()
    stage_name = "sample+step" if make_step_on_sample else "sample-only"
    status_line.log(
        f"[sample] start source={source_toml_path} output_dir={output_dir} "
        f"manifest={manifest_path} make_step_on_sample={make_step_on_sample}"
    )
    status_line.log(
        f"[sample] stage={stage_name} seeds=[{seed_first},{seed_first + seed_n}) "
        f"count={seed_n} workers={sampler_n}"
    )
    status_line.show_waiting(total=seed_n)
    config = build_type2_sample_manifest_config(
        source_toml_path=source_toml_path,
        seed_first=seed_first,
        seed_n=seed_n,
        sampler_n=sampler_n,
        make_step_on_sample=make_step_on_sample,
        aedt_builder_n=aedt_builder_n,
    )
    attempts = generate_sample_manifest_attempts(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        seed_start=seed_first,
        count=seed_n,
        jobs=sampler_n,
        make_step_on_sample=make_step_on_sample,
        exporter=exporter,
        report_progress=lambda completed, total, entry: _report_sample_progress(
            status_line,
            completed,
            total,
            entry,
        ),
        report_step_stage=lambda phase, entry: _report_sample_step_stage(
            status_line,
            phase,
            entry,
        ),
    )
    if not isinstance(attempts, dict):
        raise TypeError("generate_sample_manifest_attempts result must be a dict")
    if "entries" not in attempts:
        raise ValueError("generate_sample_manifest_attempts result is missing required key 'entries'")
    if "skipped" not in attempts:
        raise ValueError("generate_sample_manifest_attempts result is missing required key 'skipped'")
    entries = attempts["entries"]
    skipped = attempts["skipped"]
    if not isinstance(entries, list):
        raise TypeError("generate_sample_manifest_attempts result entries must be a list")
    if not isinstance(skipped, list):
        raise TypeError("generate_sample_manifest_attempts result skipped must be a list")
    for entry in skipped:
        _report_sample_skip(status_line, entry)
    document = build_type2_sample_manifest_document(
        config=config,
        entries=entries,
        skipped=skipped,
    )
    status_line.finish()
    status_line.log(
        f"[sample] stage=manifest write path={manifest_path} "
        f"count={len(entries)} skipped={len(skipped)}"
    )
    write_type2_sample_manifest(document=document, manifest_path=manifest_path)
    elapsed_s = perf_counter() - started_at
    success_count = len(entries)
    skipped_count = len(skipped)
    status_line.log(
        f"[sample] done count={success_count} skipped={skipped_count} attempted={seed_n} "
        f"manifest={manifest_path} elapsed_s={elapsed_s:.3f}"
    )
    status_line.finish()
    return document


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--build-step",
        action="store_true",
        help="Whether sample workers also export STEP artifacts.",
    )
    return parser


def run_sample_cli(argv: tuple[str, ...]) -> Type2SampleManifestDocument:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    return sample_type2(make_step_on_sample=args.build_step)


def main() -> Type2SampleManifestDocument:
    return run_sample_cli(tuple(sys.argv[1:]))


if __name__ == "__main__":
    main()
