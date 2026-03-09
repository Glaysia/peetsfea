from __future__ import annotations

from pathlib import Path

from peetsfea.pipeline.run_batch import SampleManifestEntry, generate_sample_artifact_for_seed, write_sample_manifest
from peetsfea.pipeline.uniform_seedset import generate_eager_uniform_feasible_seed_points

cwd = Path(__file__).parent.resolve()

ANSYS_EXECUTABLE_PATH = "/opt/ansys_inc/v252/AnsysEM"
SOURCE_TOML_PATH = cwd / "run" / "type1.toml"
SAMPLE_OUTPUT_DIR = cwd / "run" / "toml"
SAMPLE_MANIFEST_PATH = SAMPLE_OUTPUT_DIR / "manifest.json"
ANSYS_RUN_DIR = cwd / "run" / "aedt"

EAGER_SEED_START = 0
EAGER_SEED_END = 500
EAGER_TARGET_COUNT = 100
EAGER_MAX_ATTEMPTS = 64


def generate_sample_manifest() -> list[SampleManifestEntry]:
    entries: list[SampleManifestEntry] = []
    selected_points = generate_eager_uniform_feasible_seed_points(
        spec_path=SOURCE_TOML_PATH,
        seed_start=EAGER_SEED_START,
        seed_end=EAGER_SEED_END,
        target_size=EAGER_TARGET_COUNT,
        max_attempts=EAGER_MAX_ATTEMPTS,
    )
    print(
        "small-range eager uniform seed selection enabled "
        f"(range=[{EAGER_SEED_START},{EAGER_SEED_END}), target={EAGER_TARGET_COUNT}, "
        f"max_attempts={EAGER_MAX_ATTEMPTS})"
    )
    selected_seeds = tuple(point.seed for point in selected_points)

    for seed in selected_seeds:
        try:
            entry = generate_sample_artifact_for_seed(
                source_toml_path=SOURCE_TOML_PATH,
                output_dir=SAMPLE_OUTPUT_DIR,
                ansys_run_dir=ANSYS_RUN_DIR,
                ansys_executable_path=ANSYS_EXECUTABLE_PATH,
                seed=seed,
            )
        except Exception as exc:
            print(f"[seed={seed}] sample generation failed; skipping: {exc}")
            continue
        entries.append(entry)

    write_sample_manifest(entries, SAMPLE_MANIFEST_PATH)
    print(f"wrote sample manifest: {SAMPLE_MANIFEST_PATH}")
    return entries


if __name__ == "__main__":
    generate_sample_manifest()
