from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.console_log import info
from peetsfea.type2_step_export import export_type2_step_artifacts
from peetsfea.type2_sampled import (
    Type2SampleManifestEntry,
    Type2SampleManifestDocument,
    build_type2_sample_manifest_config,
    build_type2_sample_manifest_document,
    generate_sample_manifest_entries,
    write_type2_sample_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2_sweep.toml"
OUTPUT_DIR = REPO_ROOT / "run" / "sampled" / "type2"
MANIFEST_PATH = OUTPUT_DIR / "manifest.json"
SEED_FIRST = 0
SEED_N = 1
SAMPLER_N = 1
AEDT_BUILDER_N = 1
MAKE_STEP_ON_SAMPLE = True

_Exporter = Callable[..., object]


class _SampleStatusLine:
    def __init__(self) -> None:
        self._tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        self._active = False
        self._rendered_line = ""

    def log(self, message: str) -> None:
        self.clear()
        info(message)

    def show_waiting(self, *, total: int) -> None:
        self._render(completed=0, total=total, detail="waiting")

    def update(self, *, completed: int, total: int, entry: Type2SampleManifestEntry) -> None:
        detail = f"last_idx={entry['sample_index']} last_seed={entry['seed']}"
        self._render(completed=completed, total=total, detail=detail)

    def clear(self) -> None:
        if not self._active:
            return
        sys.stdout.write("\r")
        sys.stdout.write(" " * len(self._rendered_line))
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
        rendered_line = f"PeetsFEA INFO: {message}"
        padded_line = rendered_line
        if len(self._rendered_line) > len(rendered_line):
            padded_line = rendered_line + (" " * (len(self._rendered_line) - len(rendered_line)))
        sys.stdout.write(f"\r{padded_line}")
        sys.stdout.flush()
        self._active = True
        self._rendered_line = rendered_line


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
    entries = generate_sample_manifest_entries(
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
    )
    document = build_type2_sample_manifest_document(config=config, entries=entries)
    status_line.finish()
    status_line.log(f"[sample] stage=manifest write path={manifest_path} count={len(entries)}")
    write_type2_sample_manifest(document=document, manifest_path=manifest_path)
    elapsed_s = perf_counter() - started_at
    status_line.log(
        f"[sample] done count={len(entries)} manifest={manifest_path} elapsed_s={elapsed_s:.3f}"
    )
    return document


def main() -> Type2SampleManifestDocument:
    return sample_type2()


if __name__ == "__main__":
    main()
