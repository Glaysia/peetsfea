from __future__ import annotations

from pathlib import Path

import pytest

from peetsfea.spec.loader import load_toml_bytes
from peetsfea.legacy.type1.spec.resolver import resolve_selection
from peetsfea.legacy.type1.spec.resolver.sampling import (
    SamplingRegistry,
    SamplingRegistryEntry,
    build_sampling_registry,
    scan_sample_like_fields,
)
from tests.fixtures.legacy.type1_spec import write_type1_toml


def test_sampling_registry_covers_example_sample_like_fields(tmp_path: Path) -> None:
    toml_path = tmp_path / "type1.toml"
    write_type1_toml(toml_path)
    spec, _ = load_toml_bytes(toml_path)

    registry = build_sampling_registry(spec)
    scanned_paths = {field.path for field in scan_sample_like_fields(spec)}

    assert scanned_paths == registry.known_paths()


def test_unknown_sampled_field_fails_preflight(tmp_path: Path) -> None:
    toml_path = tmp_path / "unknown_sampling_field.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8")
    raw += "\n[unknown_sampling.extra_knob]\nrange = [false, 1.0, 2.0, 2]\n"
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"Unknown sampled field: unknown_sampling\.extra_knob"):
        resolve_selection(spec=spec, seed=1, attempt=0)


def test_duplicate_sampling_owner_registration_fails() -> None:
    entry_a = SamplingRegistryEntry(
        canonical_key="owner.a",
        owner_path="owner.a",
        sampler_kind="range",
        value_type="float",
        export_to_dataset=True,
        replay_affects_design=True,
    )
    entry_b = SamplingRegistryEntry(
        canonical_key="owner.b",
        owner_path="owner.a",
        sampler_kind="range",
        value_type="float",
        export_to_dataset=True,
        replay_affects_design=True,
    )

    with pytest.raises(ValueError, match=r"Duplicate sampling owner path: owner\.a"):
        SamplingRegistry(entries=(entry_a, entry_b))


def test_normalized_away_present_field_must_be_fixed(tmp_path: Path) -> None:
    toml_path = tmp_path / "normalized_away_present.toml"
    write_type1_toml(toml_path)
    raw = toml_path.read_text(encoding="utf-8").replace(
        "present = [true, 0, 0, 1]",
        "present = [true, 0, 1, 2]",
        1,
    )
    toml_path.write_text(raw, encoding="utf-8")

    spec, _ = load_toml_bytes(toml_path)
    with pytest.raises(ValueError, match=r"normalized-away sampled field must be fixed with count=1: pcbs\[\d+\]\.present"):
        resolve_selection(spec=spec, seed=1, attempt=0)
