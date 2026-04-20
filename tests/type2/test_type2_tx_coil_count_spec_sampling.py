from __future__ import annotations

from pathlib import Path

import pytest

from peetsfea.type2_sampled import exportable_sampled_owner_paths
from peetsfea.type2_sampled import sampled_owner_values
from peetsfea.type2_step_spec import ModeledTxPlateStackSpec
from peetsfea.type2_step_spec import load_type2_step_spec
from peetsfea.type2_step_spec import resolve_modeled_tx_array_x_usage_ratio
from peetsfea.type2_step_spec import resolve_modeled_tx_coil_count


def _type2_plate_stack_toml(
    *,
    tx_tx_coil_count_range: str,
    tx_array_x_usage_ratio_range: str = "[false, 1.0, 1.0, 1]",
    rx_tx_only_block: str = "",
) -> str:
    return f"""
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v6"
runtime_compatible = false

[design]
units = "mm"

[backend]
authoring_tool = "build123d"
solver_tool = "hfss"
interchange_format = "step"

[simulation]
radiation_margin_mm = 3500.0

[outputs]
report_name = "Output Variables Table1"
solution_name = "Setup1 : LastAdaptive"
primary_sweep = "Freq"
report_category = "Terminal Solution Data"
plot_type = "Data Table"

[[outputs.variables]]
name = "Ltx_uH"
expression = "im(Zt(TX_TML,TX_TML))/2/pi/freq*1e6"

[[non_model_objects]]
id = "tx_region"
kind = "tx_region"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [0.0, -140.0, 0.0]
size_xyz = [160.0, 280.0, 90.0]

[[non_model_objects]]
id = "rx_region_max"
kind = "rx_region_max"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [200.0, -100.0, 0.0]
size_xyz = [10.0, 200.0, 200.0]

[[non_model_objects]]
id = "tx_region_actual"
kind = "tx_region_actual"
source_region_id = "tx_region"
[non_model_objects.x_usage_ratio]
range = [false, 0.3, 0.3, 1]
[non_model_objects.y_usage_ratio]
range = [false, 0.3, 0.3, 1]
[non_model_objects.x_division_count]
range = [true, 1, 1, 1]
[non_model_objects.y_division_count]
range = [true, 1, 1, 1]

[[modeled_objects]]
object_id = "tx_plate_stack"
role = "tx_plate_stack"
material = "composite"
model_state = true
pcb_total_thickness_mm = 0.4
copper_thickness_mm = 0.035
[modeled_objects.turn_count]
range = [true, 2, 5, 4]
[modeled_objects.metal_fill_factor]
range = [false, 0.2, 0.6, 15]
[modeled_objects.z_usage_ratio]
range = [false, 0.03, 0.6, 17]
[modeled_objects.y_usage_ratio]
range = [false, 0.03, 0.6, 17]
[modeled_objects.tx_coil_count]
range = {tx_tx_coil_count_range}
[modeled_objects.tx_array_x_usage_ratio]
range = {tx_array_x_usage_ratio_range}

[[modeled_objects]]
object_id = "rx_plate_stack"
role = "rx_plate_stack"
material = "composite"
model_state = true
pcb_total_thickness_mm = 0.4
copper_thickness_mm = 0.1
[modeled_objects.turn_count]
range = [true, 2, 5, 4]
[modeled_objects.metal_fill_factor]
range = [false, 0.2, 0.6, 15]
[modeled_objects.z_usage_ratio]
range = [false, 0.03, 0.6, 17]
[modeled_objects.y_usage_ratio]
range = [false, 0.03, 0.6, 17]
{rx_tx_only_block}
""".strip()


def _write_toml(tmp_path: Path, *, text: str) -> Path:
    path = tmp_path / "type2_tx_plate_stack.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _tx_spec_from_loaded_spec(toml_path: Path) -> ModeledTxPlateStackSpec:
    spec = load_type2_step_spec(toml_path)
    tx_specs = [modeled_spec for modeled_spec in spec.modeled_objects if modeled_spec.role == "tx_plate_stack"]
    assert len(tx_specs) == 1
    tx_spec = tx_specs[0]
    assert isinstance(tx_spec, ModeledTxPlateStackSpec)
    return tx_spec


def test_tx_coil_count_accepts_canonical_and_fixed_ranges_and_resolves(tmp_path: Path) -> None:
    canonical_path = _write_toml(
        tmp_path,
        text=_type2_plate_stack_toml(tx_tx_coil_count_range="[true, 1, 4, 4]"),
    )
    canonical_tx_spec = _tx_spec_from_loaded_spec(canonical_path)
    fixed_path = _write_toml(
        tmp_path,
        text=_type2_plate_stack_toml(tx_tx_coil_count_range="[true, 2, 2, 1]"),
    )
    fixed_tx_spec = _tx_spec_from_loaded_spec(fixed_path)

    canonical_value = resolve_modeled_tx_coil_count(canonical_tx_spec, seed=19)
    fixed_value = resolve_modeled_tx_coil_count(fixed_tx_spec, seed=19)

    assert canonical_value in {1, 2, 3, 4}
    assert fixed_value == 2


def test_tx_array_x_usage_ratio_accepts_canonical_and_fixed_ranges_and_resolves(tmp_path: Path) -> None:
    canonical_path = _write_toml(
        tmp_path,
        text=_type2_plate_stack_toml(
            tx_tx_coil_count_range="[true, 1, 4, 4]",
            tx_array_x_usage_ratio_range="[false, 0.1, 0.6, 14]",
        ),
    )
    canonical_tx_spec = _tx_spec_from_loaded_spec(canonical_path)
    fixed_path = _write_toml(
        tmp_path,
        text=_type2_plate_stack_toml(
            tx_tx_coil_count_range="[true, 2, 2, 1]",
            tx_array_x_usage_ratio_range="[false, 1.0, 1.0, 1]",
        ),
    )
    fixed_tx_spec = _tx_spec_from_loaded_spec(fixed_path)

    canonical_value = resolve_modeled_tx_array_x_usage_ratio(canonical_tx_spec, seed=19)
    fixed_value = resolve_modeled_tx_array_x_usage_ratio(fixed_tx_spec, seed=19)

    assert 0.1 <= canonical_value <= 0.6
    assert fixed_value == pytest.approx(1.0)


def test_tx_coil_count_rejects_noncanonical_nonfixed_range(tmp_path: Path) -> None:
    toml_path = _write_toml(
        tmp_path,
        text=_type2_plate_stack_toml(tx_tx_coil_count_range="[true, 1, 4, 3]"),
    )
    with pytest.raises(ValueError, match=r"tx_coil_count\.range must be canonical \[true, 1, 4, 4\]"):
        load_type2_step_spec(toml_path)


def test_tx_array_x_usage_ratio_rejects_noncanonical_nonfixed_range(tmp_path: Path) -> None:
    toml_path = _write_toml(
        tmp_path,
        text=_type2_plate_stack_toml(
            tx_tx_coil_count_range="[true, 1, 4, 4]",
            tx_array_x_usage_ratio_range="[false, 0.1, 0.6, 13]",
        ),
    )
    with pytest.raises(
        ValueError,
        match=r"tx_array_x_usage_ratio\.range must be canonical \[false, 0\.1, 0\.6, 14\]",
    ):
        load_type2_step_spec(toml_path)


@pytest.mark.parametrize(
    ("rx_tx_only_block", "match"),
    [
        ("[modeled_objects.tx_coil_count]\nrange = [true, 1, 1, 1]", r"tx_coil_count is unsupported"),
        (
            "[modeled_objects.tx_array_x_usage_ratio]\nrange = [false, 1.0, 1.0, 1]",
            r"tx_array_x_usage_ratio is unsupported",
        ),
    ],
)
def test_rx_plate_stack_rejects_tx_only_array_fields(
    tmp_path: Path,
    rx_tx_only_block: str,
    match: str,
) -> None:
    toml_path = _write_toml(
        tmp_path,
        text=_type2_plate_stack_toml(
            tx_tx_coil_count_range="[true, 1, 4, 4]",
            rx_tx_only_block=rx_tx_only_block,
        ),
    )
    with pytest.raises(ValueError, match=match):
        load_type2_step_spec(toml_path)


def test_sampling_owner_paths_and_values_include_tx_coil_count_after_tx_y_usage_ratio(tmp_path: Path) -> None:
    toml_path = _write_toml(
        tmp_path,
        text=_type2_plate_stack_toml(
            tx_tx_coil_count_range="[true, 1, 4, 4]",
            tx_array_x_usage_ratio_range="[false, 0.1, 0.6, 14]",
        ),
    )
    spec = load_type2_step_spec(toml_path)

    owner_paths = list(exportable_sampled_owner_paths(spec))
    tx_y_usage_ratio_index = owner_paths.index("modeled_objects.tx_plate_stack.y_usage_ratio")
    assert owner_paths[tx_y_usage_ratio_index + 1] == "modeled_objects.tx_plate_stack.tx_coil_count"
    assert owner_paths[tx_y_usage_ratio_index + 2] == "modeled_objects.tx_plate_stack.tx_array_x_usage_ratio"

    sampled_value_map = dict(sampled_owner_values(spec, seed=77))
    tx_coil_count = sampled_value_map["modeled_objects.tx_plate_stack.tx_coil_count"]
    tx_array_x_usage_ratio = sampled_value_map["modeled_objects.tx_plate_stack.tx_array_x_usage_ratio"]
    assert isinstance(tx_coil_count, int)
    assert tx_coil_count in {1, 2, 3, 4}
    assert isinstance(tx_array_x_usage_ratio, float)
    assert 0.1 <= tx_array_x_usage_ratio <= 0.6
