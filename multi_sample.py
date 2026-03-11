from __future__ import annotations

from peetsfea.pipeline.run_batch import SampleManifestEntry

from sample import SampleProfile, generate_sample_manifest, sample_manifest_path_for_seed_start

SAMPLE_PROFILES: tuple[SampleProfile, ...] = (
    SampleProfile(seed_start=0+500*i, seed_end=500+500*i, target_count=100) for i in range(10)
    ) # type: ignore


def generate_all_sample_manifests(
    profiles: tuple[SampleProfile, ...] = SAMPLE_PROFILES,
) -> list[list[SampleManifestEntry]]:
    results: list[list[SampleManifestEntry]] = []
    for profile in profiles:
        print(
            f"[multi_sample] start range=[{profile.seed_start},{profile.seed_end}) "
            f"target={profile.target_count}"
        )
        entries = generate_sample_manifest(
            seed_start=profile.seed_start,
            seed_end=profile.seed_end,
            target_count=profile.target_count,
        )
        manifest_path = sample_manifest_path_for_seed_start(profile.seed_start)
        print(f"[multi_sample] wrote {len(entries)} entries to {manifest_path}")
        results.append(entries)
    return results


if __name__ == "__main__":
    generate_all_sample_manifests()
