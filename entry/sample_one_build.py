from __future__ import annotations

import sys

if __package__ in {None, ""}:
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from entry.build_one import SampleBuildBatchResult, generate_and_build_profile
from entry.sample import SampleProfile

DEFAULT_SAMPLE_ONE_BUILD_PROFILE = SampleProfile(seed_start=0, seed_end=500, target_count=1)


def sample_one_build(profile: SampleProfile = DEFAULT_SAMPLE_ONE_BUILD_PROFILE) -> SampleBuildBatchResult:
    return generate_and_build_profile(profile)


if __name__ == "__main__":
    sample_one_build()
