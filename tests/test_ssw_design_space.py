from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from peetsfea.ssw_step import load_ssw_fixed_spec
from peetsfea.ssw_design_space import (
    build_ssw_aedt_identity,
    check_ssw_toml_in_design_space,
    sample_ssw_fixed_tomls,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXED_TOML = REPO_ROOT / "examples" / "0.3.0_fixed.toml"
SWEEP_TOML = REPO_ROOT / "examples" / "0.3.0_sweep.toml"


def _candidate(tmp_path: Path, text: str) -> Path:
    candidate_path = tmp_path / "candidate.toml"
    candidate_path.write_text(text, encoding="utf-8")
    return candidate_path


def _replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise AssertionError(f"test fixture text is missing expected snippet: {old!r}")
    return text.replace(old, new, 1)


def _violation_codes_by_path(result_path: Path) -> dict[str, set[str]]:
    result = check_ssw_toml_in_design_space(result_path, SWEEP_TOML)
    codes_by_path: dict[str, set[str]] = {}
    for violation in result.violations:
        if violation.path not in codes_by_path:
            codes_by_path[violation.path] = set()
        codes_by_path[violation.path].add(violation.code)
    return codes_by_path


def _fixed_dimension_range(toml_path: Path, key: str) -> list[object]:
    raw_root = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    root = _require_test_table(raw_root, toml_path.name)
    fixed_dimensions = _require_test_table(root["fixed_dimensions"], "fixed_dimensions")
    child = _require_test_table(fixed_dimensions[key], f"fixed_dimensions.{key}")
    raw_range = child["range"]
    if isinstance(raw_range, (str, bytes)) or not isinstance(raw_range, list):
        raise AssertionError(f"fixed_dimensions.{key}.range must be a list")
    return raw_range


def _require_test_table(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise AssertionError(f"{context} must be a table")
    return value


def test_fixed_toml_is_reference_design_space_point() -> None:
    result = check_ssw_toml_in_design_space(FIXED_TOML, SWEEP_TOML)

    assert result.is_subset is True
    assert result.is_point is True
    assert result.dimension_count == 29
    assert len(result.free_owner_paths) == 29
    assert result.violations == ()
    assert "ferrite.tx_mull_position_ratio" in result.free_owner_paths
    assert "ferrite.rx_mull_position_ratio" in result.free_owner_paths
    assert "ferrite.tx_mull_is_enabled" not in result.free_owner_paths
    assert "ferrite.rx_mull_is_enabled" not in result.free_owner_paths
    assert "modeled_objects[role=tx_under_coil].is_under_coil_enabled" in result.free_owner_paths
    assert "modeled_objects[role=tx_under_coil].width_ratio" in result.free_owner_paths
    assert "modeled_objects[role=tx_under_coil].height_ratio" in result.free_owner_paths
    assert "modeled_objects[role=tx_under_coil].turn_n_int" in result.free_owner_paths
    assert "modeled_objects[role=tx_under_coil].gap_ratio" in result.free_owner_paths
    assert "modeled_objects[role=tx_under_coil].void_area_ratio" in result.free_owner_paths
    assert "modeled_objects[role=tx_under_coil].void_profile" in result.free_owner_paths
    assert "modeled_objects[role=tx_under_coil].no_ssw_qturn_start_int" not in result.free_owner_paths
    assert "modeled_objects[role=tx_under_coil].no_ssw_qturn_n_int" not in result.free_owner_paths
    assert "modeled_objects[role=rx_ssw_coil].is_ssw_enabled" in result.free_owner_paths


def test_aedt_identity_is_deterministic_short_point_name() -> None:
    first = build_ssw_aedt_identity(FIXED_TOML, SWEEP_TOML)
    second = build_ssw_aedt_identity(FIXED_TOML, SWEEP_TOML)

    assert first == second
    assert first.dimension_count == 29
    assert len(first.point_hash) == 16
    assert first.design_id == f"0_3_0_p{first.point_hash}"
    assert first.aedt_filename == f"{first.design_id}.aedt"
    assert "ssw" not in first.design_id


def test_point_hash_tracks_realized_continuous_values(tmp_path: Path) -> None:
    base_identity = build_ssw_aedt_identity(FIXED_TOML, SWEEP_TOML)
    text = _replace_once(
        FIXED_TOML.read_text(encoding="utf-8"),
        "[modeled_objects.width_ratio]\nrange = [false, 0.45, 0.45, 1]",
        "[modeled_objects.width_ratio]\nrange = [false, 0.4501, 0.4501, 1]",
    )
    changed_path = _candidate(tmp_path, text)
    changed_identity = build_ssw_aedt_identity(changed_path, SWEEP_TOML)

    assert changed_identity.dimension_count == base_identity.dimension_count
    assert changed_identity.point_hash != base_identity.point_hash
    assert changed_identity.design_id != base_identity.design_id


def test_narrow_range_with_larger_count_is_subset_but_not_point(tmp_path: Path) -> None:
    text = _replace_once(
        FIXED_TOML.read_text(encoding="utf-8"),
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 100.0, 100.0, 1]",
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 60.0, 70.0, 200]",
    )
    candidate_path = _candidate(tmp_path, text)

    result = check_ssw_toml_in_design_space(candidate_path, SWEEP_TOML)

    assert result.is_subset is True
    assert result.is_point is False
    assert result.violations == ()
    with pytest.raises(ValueError, match="requires a single realized point"):
        build_ssw_aedt_identity(candidate_path, SWEEP_TOML)


def test_out_of_reference_range_reports_violation(tmp_path: Path) -> None:
    text = _replace_once(
        FIXED_TOML.read_text(encoding="utf-8"),
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 100.0, 100.0, 1]",
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 40.0, 50.0, 1]",
    )
    candidate_path = _candidate(tmp_path, text)

    result = check_ssw_toml_in_design_space(candidate_path, SWEEP_TOML)

    assert result.is_subset is False
    assert result.is_point is False
    assert result.violations[0].path == "fixed_dimensions.tx_rx_min_distance_mm"
    assert result.violations[0].code == "lower_bound_outside_reference"


def test_missing_path_integer_flag_mismatch_and_non_positive_count_are_violations(tmp_path: Path) -> None:
    text = FIXED_TOML.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "[ferrite.tx_mull_position_ratio]\nrange = [false, 0.0, 0.0, 1]",
        "[ferrite.tx_mull_position_ratio_removed]\nrange = [false, 0.0, 0.0, 1]",
    )
    text = _replace_once(
        text,
        "[modeled_objects.is_under_coil_enabled]\nrange = [true, 0, 0, 1]",
        "[modeled_objects.is_under_coil_enabled]\nrange = [false, 0, 0, 1]",
    )
    text = _replace_once(
        text,
        "[modeled_objects.turn_n_int]\nrange = [true, 3, 3, 1]",
        "[modeled_objects.turn_n_int]\nrange = [true, 3, 3, 0]",
    )
    candidate_path = _candidate(tmp_path, text)

    codes_by_path = _violation_codes_by_path(candidate_path)

    assert codes_by_path["ferrite.tx_mull_position_ratio"] == {"missing_free_path"}
    assert codes_by_path["modeled_objects[role=tx_under_coil].is_under_coil_enabled"] == {"integer_flag_mismatch"}
    assert codes_by_path["modeled_objects[role=tx_ssw_coil].turn_n_int"] == {"non_positive_count"}


def test_sample_ssw_fixed_tomls_generates_valid_unique_points(tmp_path: Path) -> None:
    output_dir = tmp_path / "samples"

    batch = sample_ssw_fixed_tomls(3, 123, SWEEP_TOML, output_dir, SWEEP_TOML)

    assert batch.sample_count == 3
    assert batch.seed == 123
    assert batch.source_toml_path == SWEEP_TOML
    assert batch.reference_toml_path == SWEEP_TOML
    assert batch.output_dir == output_dir
    assert batch.dimension_count == 29
    assert len(batch.samples) == 3
    assert len({sample.design_id for sample in batch.samples}) == 3
    for expected_index, sample in enumerate(batch.samples):
        assert sample.index == expected_index
        assert sample.toml_path == output_dir / f"{sample.design_id}.toml"
        assert sample.toml_path.exists()
        result = check_ssw_toml_in_design_space(sample.toml_path, SWEEP_TOML)
        assert result.is_subset is True
        assert result.is_point is True
        load_ssw_fixed_spec(sample.toml_path)
        identity = build_ssw_aedt_identity(sample.toml_path, SWEEP_TOML)
        assert sample.design_id == identity.design_id
        assert sample.aedt_filename == identity.aedt_filename
        assert sample.point_hash == identity.point_hash


def test_sample_ssw_fixed_tomls_is_reproducible_for_same_seed(tmp_path: Path) -> None:
    first = sample_ssw_fixed_tomls(2, 456, SWEEP_TOML, tmp_path / "first", SWEEP_TOML)
    second = sample_ssw_fixed_tomls(2, 456, SWEEP_TOML, tmp_path / "second", SWEEP_TOML)

    assert tuple(sample.design_id for sample in first.samples) == tuple(sample.design_id for sample in second.samples)
    assert tuple(sample.point_hash for sample in first.samples) == tuple(sample.point_hash for sample in second.samples)
    assert tuple(sample.toml_path.read_text(encoding="utf-8") for sample in first.samples) == tuple(
        sample.toml_path.read_text(encoding="utf-8") for sample in second.samples
    )


def test_sample_ssw_fixed_tomls_accepts_narrow_subset_with_larger_count(tmp_path: Path) -> None:
    text = _replace_once(
        FIXED_TOML.read_text(encoding="utf-8"),
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 100.0, 100.0, 1]",
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 60.0, 70.0, 200]",
    )
    candidate_path = _candidate(tmp_path, text)

    batch = sample_ssw_fixed_tomls(2, 789, candidate_path, tmp_path / "samples", SWEEP_TOML)

    assert len(batch.samples) == 2
    for sample in batch.samples:
        sampled_range = _fixed_dimension_range(sample.toml_path, "tx_rx_min_distance_mm")
        assert sampled_range[0] is False
        assert sampled_range[1] == sampled_range[2]
        assert sampled_range[3] == 1
        sampled_value = sampled_range[1]
        assert isinstance(sampled_value, float)
        assert 60.0 <= sampled_value <= 70.0


def test_sample_ssw_fixed_tomls_rejects_out_of_reference_input_before_output(tmp_path: Path) -> None:
    text = _replace_once(
        FIXED_TOML.read_text(encoding="utf-8"),
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 100.0, 100.0, 1]",
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 40.0, 50.0, 1]",
    )
    candidate_path = _candidate(tmp_path, text)
    output_dir = tmp_path / "samples"

    with pytest.raises(ValueError, match="outside the reference design space"):
        sample_ssw_fixed_tomls(1, 321, candidate_path, output_dir, SWEEP_TOML)

    assert not output_dir.exists()


def test_sample_ssw_fixed_tomls_fails_when_constraints_cannot_be_satisfied(tmp_path: Path) -> None:
    text = FIXED_TOML.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "[modeled_objects.turn_n_int]\nrange = [true, 3, 3, 1]",
        "[modeled_objects.turn_n_int]\nrange = [true, 4, 4, 1]",
    )
    text = _replace_once(
        text,
        "[modeled_objects.twist_factor]\nrange = [true, 2, 2, 1]",
        "[modeled_objects.twist_factor]\nrange = [true, 2, 2, 1]",
    )
    candidate_path = _candidate(tmp_path, text)
    output_dir = tmp_path / "samples"

    with pytest.raises(RuntimeError, match="failed to generate SSW sample 0 after 2 attempts"):
        sample_ssw_fixed_tomls(1, 654, candidate_path, output_dir, SWEEP_TOML, max_attempts_per_sample=2)

    assert tuple(output_dir.iterdir()) == ()


def test_sample_ssw_fixed_tomls_fails_when_unique_points_are_exhausted(tmp_path: Path) -> None:
    output_dir = tmp_path / "samples"

    with pytest.raises(RuntimeError, match="duplicate sampled design_id"):
        sample_ssw_fixed_tomls(2, 987, FIXED_TOML, output_dir, SWEEP_TOML, max_attempts_per_sample=2)

    assert len(tuple(output_dir.glob("*.toml"))) == 1
