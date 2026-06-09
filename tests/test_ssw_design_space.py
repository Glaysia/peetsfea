from __future__ import annotations

from pathlib import Path

import pytest

from peetsfea.ssw_design_space import (
    build_ssw_aedt_identity,
    check_ssw_toml_in_design_space,
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


def test_fixed_toml_is_reference_design_space_point() -> None:
    result = check_ssw_toml_in_design_space(FIXED_TOML, SWEEP_TOML)

    assert result.is_subset is True
    assert result.is_point is True
    assert result.dimension_count == 21
    assert len(result.free_owner_paths) == 21
    assert result.violations == ()
    assert "modeled_objects[role=rx_ssw_coil].is_ssw_enabled" in result.free_owner_paths


def test_aedt_identity_is_deterministic_short_point_name() -> None:
    first = build_ssw_aedt_identity(FIXED_TOML, SWEEP_TOML)
    second = build_ssw_aedt_identity(FIXED_TOML, SWEEP_TOML)

    assert first == second
    assert first.dimension_count == 21
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
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 50.0, 50.0, 1]",
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
        "[fixed_dimensions.tx_rx_min_distance_mm]\nrange = [false, 50.0, 50.0, 1]",
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
        "[ferrite.mull_position_ratio]\nrange = [false, 0.0, 0.0, 1]",
        "[ferrite.mull_position_ratio_removed]\nrange = [false, 0.0, 0.0, 1]",
    )
    text = _replace_once(
        text,
        "[modeled_objects.is_ssw_enabled]\nrange = [true, 0, 0, 1]",
        "[modeled_objects.is_ssw_enabled]\nrange = [false, 0, 0, 1]",
    )
    text = _replace_once(
        text,
        "[modeled_objects.turn_n_int]\nrange = [true, 6, 6, 1]",
        "[modeled_objects.turn_n_int]\nrange = [true, 6, 6, 0]",
    )
    candidate_path = _candidate(tmp_path, text)

    codes_by_path = _violation_codes_by_path(candidate_path)

    assert codes_by_path["ferrite.mull_position_ratio"] == {"missing_free_path"}
    assert codes_by_path["modeled_objects[role=rx_ssw_coil].is_ssw_enabled"] == {"integer_flag_mismatch"}
    assert codes_by_path["modeled_objects[role=tx_ssw_coil].turn_n_int"] == {"non_positive_count"}
