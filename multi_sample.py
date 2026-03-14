from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from os import cpu_count

from peetsfea.pipeline.run_batch import SampleManifestEntry

from sample import SampleProfile, generate_sample_manifest, sample_manifest_path_for_seed_start
N = 1
SAMPLE_PROFILES: tuple[SampleProfile, ...] = tuple(
    SampleProfile(seed_start=500 * i, seed_end=500 * (i + 1), target_count=100)
    for i in range(N)
)
SAMPLE_WORKER_COUNT = N


def _generate_profile_manifest(profile: SampleProfile) -> list[SampleManifestEntry]:
    return generate_sample_manifest(
        seed_start=profile.seed_start,
        seed_end=profile.seed_end,
        target_count=profile.target_count,
    )


def generate_all_sample_manifests(
    profiles: tuple[SampleProfile, ...] = SAMPLE_PROFILES,
    *,
    parallel: bool = True,
    max_workers: int | None = None,
) -> list[list[SampleManifestEntry]]:
    if not profiles:
        return []

    results: list[list[SampleManifestEntry]] = []
    for profile in profiles:
        print(
            f"[multi_sample] start range=[{profile.seed_start},{profile.seed_end}) "
            f"target={profile.target_count}"
        )

    if not parallel:
        for profile in profiles:
            entries = _generate_profile_manifest(profile)
            manifest_path = sample_manifest_path_for_seed_start(profile.seed_start)
            print(f"[multi_sample] wrote {len(entries)} entries to {manifest_path}")
            results.append(entries)
        return results

    worker_count = max_workers or min(len(profiles), SAMPLE_WORKER_COUNT)
    with ProcessPoolExecutor(max_workers=worker_count) as executor:
        for profile, entries in zip(profiles, executor.map(_generate_profile_manifest, profiles), strict=True):
            manifest_path = sample_manifest_path_for_seed_start(profile.seed_start)
            print(f"[multi_sample] wrote {len(entries)} entries to {manifest_path}")
            results.append(entries)
    return results


if __name__ == "__main__":
    generate_all_sample_manifests()
