from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from peetsfea.spec.toml_render import toml_dumps
from peetsfea.spec.loader import load_toml_bytes
from peetsfea.type2_sampled_sampling import _all_range_owner_specs
from peetsfea.type2_step_spec import Type2StepSpec
from peetsfea.type2_step_spec import load_type2_step_spec


REPO_ROOT = Path(__file__).resolve().parents[2]
TYPE2_SWEEP_TOML = REPO_ROOT / "examples" / "type2_sweep.toml"
TYPE2_FIXED_TOML = REPO_ROOT / "examples" / "type2_fixed.toml"


def _load_type2_spec_tools() -> ModuleType:
    return importlib.import_module("peetsfea.type2_spec_tools")


def _write_toml_with_constraint(
    tmp_path: Path,
    *,
    constraint_text: str,
    name: str = "constrained_type2.toml",
) -> Path:
    toml_path = tmp_path / name
    source_text = TYPE2_SWEEP_TOML.read_text(encoding="utf-8")
    constraints_header = "" if "\n[constraints]\n" in source_text else "[constraints]\n\n"
    rendered_text = f"{source_text.rstrip()}\n\n{constraints_header}{constraint_text.strip()}\n"
    toml_path.write_text(rendered_text, encoding="utf-8")
    return toml_path


def _owner_description_table_lines(
    tmp_path: Path,
    *,
    owner_path: str,
    mutation: str,
) -> Path:
    raw_spec, _raw_bytes = load_toml_bytes(TYPE2_SWEEP_TOML)
    owner_field = _range_owner_field_from_path(raw_spec, owner_path=owner_path)
    if mutation == "missing":
        del owner_field["description"]
    elif mutation == "empty":
        owner_field["description"] = ""
    elif mutation == "nonstr":
        owner_field["description"] = 123
    else:
        raise AssertionError(f"unknown mutation: {mutation}")

    mutated_path = tmp_path / f"{mutation}_{owner_path.replace('.', '_')}.toml"
    mutated_text = toml_dumps(raw_spec)
    mutated_path.write_text(mutated_text, encoding="utf-8")
    return mutated_path


def _range_owner_field_from_path(
    raw_spec: object,
    *,
    owner_path: str,
) -> dict[str, object]:
    if not isinstance(raw_spec, dict):
        raise TypeError("type2 spec root must be a table")
    owner_parts = owner_path.split(".")
    if len(owner_parts) < 3:
        raise ValueError(f"unsupported owner path: {owner_path}")
    owner_root, object_id = owner_parts[0], owner_parts[1]
    if owner_root == "modeled_objects":
        raw_objects = raw_spec["modeled_objects"]
        id_key = "object_id"
    elif owner_root == "non_model_objects":
        raw_objects = raw_spec["non_model_objects"]
        id_key = "id"
    else:
        raise ValueError(f"unsupported owner root: {owner_path}")
    if not isinstance(raw_objects, list):
        raise TypeError(f"{owner_root} must be an array of tables")

    object_table: dict[str, object] | None = None
    for entry in raw_objects:
        if not isinstance(entry, dict):
            raise TypeError(f"{owner_root} entries must be tables")
        if id_key not in entry:
            raise ValueError(f"{owner_root} entry is missing {id_key}")
        raw_id = entry[id_key]
        if isinstance(raw_id, str) and raw_id == object_id:
            object_table = entry
            break
    assert object_table is not None

    for table_name in owner_parts[2:]:
        raw_table = object_table[table_name]
        if not isinstance(raw_table, dict):
            raise TypeError(f"{owner_path} path segment {table_name!r} must be a table")
        object_table = raw_table
    return object_table


def _range_owner_paths(path: Path) -> tuple[str, ...]:
    return tuple(owner_path for owner_path, _range_spec in _all_range_owner_specs(load_type2_step_spec(path)))


def _assert_complete_range_owner_descriptions(path: Path) -> None:
    tools = _load_type2_spec_tools()
    descriptions = cast(dict[str, str], tools.type2_range_owner_descriptions(path))
    assert tuple(descriptions) == _range_owner_paths(path)
    assert all(description != "" for description in descriptions.values())


def _single_retry_constraint_for_public_sampling(spec: Type2StepSpec, *, seed: int) -> tuple[str, int | float, int]:
    from peetsfea.type2_sampled import sampled_owner_values

    retry_zero_values = dict(sampled_owner_values(spec, seed=seed, retry_number=0))
    for retry_number in range(1, 8):
        retry_values = dict(sampled_owner_values(spec, seed=seed, retry_number=retry_number))
        for owner_path, retry_value in retry_values.items():
            if not owner_path.startswith("modeled_objects."):
                continue
            assert owner_path in retry_zero_values
            if retry_zero_values[owner_path] != retry_value:
                return owner_path, retry_value, retry_number
    raise AssertionError("expected at least one sampled owner value to differ across retry attempts")


def _sampled_owner_value_mapping(spec: Type2StepSpec, *, seed: int) -> dict[str, int | float]:
    from peetsfea.type2_sampled_sampling import sampled_owner_values

    return dict(sampled_owner_values(spec, seed=seed))


def test_type2_spec_tools_import_does_not_load_cad_or_aedt_modules() -> None:
    sys.modules.pop("peetsfea.type2_spec_tools", None)
    for module_name in tuple(sys.modules):
        if module_name in {"build123d", "cadquery", "pyaedt"} or module_name.startswith(
            ("build123d.", "cadquery.", "pyaedt.")
        ):
            sys.modules.pop(module_name)

    _load_type2_spec_tools()

    assert "build123d" not in sys.modules
    assert "cadquery" not in sys.modules
    assert "pyaedt" not in sys.modules


def test_type2_sampled_toml_from_values_renders_loadable_toml(tmp_path: Path) -> None:
    tools = _load_type2_spec_tools()
    source_spec = load_type2_step_spec(TYPE2_SWEEP_TOML)
    owner_values = _sampled_owner_value_mapping(source_spec, seed=0)

    sampled_toml_text = tools.type2_sampled_toml_from_values(
        source_toml_path=TYPE2_SWEEP_TOML,
        owner_values=owner_values,
        seed=0,
        sample_index=0,
        head_hash4="abcd",
        retry_number=0,
    )

    sampled_toml_path = tmp_path / "sampled.toml"
    sampled_toml_path.write_text(sampled_toml_text, encoding="utf-8")
    sampled_spec = load_type2_step_spec(sampled_toml_path)

    assert len(sampled_spec.modeled_objects) == len(source_spec.modeled_objects)


@pytest.mark.parametrize(
    "mutator,expected",
    (
        (
            lambda values: {key: value for index, (key, value) in enumerate(values.items()) if index != 0},
            "missing",
        ),
        (
            lambda values: {**values, "modeled_objects.rx_rect_void_coil.not_a_real_owner": 1.0},
            "extra",
        ),
    ),
)
def test_type2_sampled_toml_from_values_rejects_owner_path_drift(
    mutator: Callable[[dict[str, int | float]], dict[str, int | float]],
    expected: str,
) -> None:
    tools = _load_type2_spec_tools()
    source_spec = load_type2_step_spec(TYPE2_SWEEP_TOML)
    owner_values = _sampled_owner_value_mapping(source_spec, seed=7)
    drifted_owner_values = mutator(owner_values)
    assert isinstance(drifted_owner_values, Mapping)

    with pytest.raises(ValueError, match=expected):
        tools.type2_sampled_toml_from_values(
            source_toml_path=TYPE2_SWEEP_TOML,
            owner_values=drifted_owner_values,
            seed=7,
            sample_index=0,
            head_hash4="abcd",
            retry_number=0,
        )


def test_type2_range_owner_descriptions_for_official_sweep_example() -> None:
    _assert_complete_range_owner_descriptions(TYPE2_SWEEP_TOML)


def test_type2_range_owner_descriptions_for_fixed_official_example() -> None:
    _assert_complete_range_owner_descriptions(TYPE2_FIXED_TOML)


@pytest.mark.parametrize(
    "owner_path,mutation,expected_exc,expected_msg",
    (
        (
            "non_model_objects.tx_region.tx_reference_line.x_ratio",
            "missing",
            ValueError,
            "must provide a non-empty description",
        ),
        (
            "modeled_objects.rx_rect_void_coil.outer_x_usage_ratio",
            "empty",
            ValueError,
            "must be non-empty",
        ),
        (
            "modeled_objects.rx_rect_void_coil.outer_y_usage_ratio",
            "nonstr",
            TypeError,
            "must be str",
        ),
    ),
)
def test_type2_range_owner_descriptions_rejects_invalid_descriptions(
    tmp_path: Path,
    owner_path: str,
    mutation: str,
    expected_exc: type[BaseException],
    expected_msg: str,
) -> None:
    mutated_toml = _owner_description_table_lines(
        tmp_path,
        owner_path=owner_path,
        mutation=mutation,
    )
    tools = _load_type2_spec_tools()

    with pytest.raises(expected_exc, match=expected_msg):
        tools.type2_range_owner_descriptions(mutated_toml)


def test_load_type2_step_spec_rejects_constraint_unknown_tx_inner_owner(tmp_path: Path) -> None:
    toml_path = _write_toml_with_constraint(
        tmp_path,
        constraint_text="""
[[constraints.rules]]
id = "bad_tx_inner_owner"
kind = "comparison"
message = "invalid tx inner owner must fail"
lhs = { path = "modeled_objects.not_tx_inner_rect_void_coil.outer_x_usage_ratio" }
op = ">="
rhs = { value = 0.1 }
""",
    )

    with pytest.raises(ValueError, match="unknown owner path"):
        load_type2_step_spec(toml_path)


def test_load_type2_step_spec_rejects_unknown_constraint_function(tmp_path: Path) -> None:
    toml_path = _write_toml_with_constraint(
        tmp_path,
        constraint_text="""
[[constraints.rules]]
id = "bad_function"
kind = "comparison"
message = "unknown function must fail"
lhs = { func = "mean(modeled_objects.tx_inner_rect_void_coil.outer_x_usage_ratio)" }
op = ">="
rhs = { value = 0.1 }
""",
    )

    with pytest.raises(ValueError, match="must be one of"):
        load_type2_step_spec(toml_path)


def test_public_sample_manifest_retries_constraints_without_step_export(tmp_path: Path) -> None:
    from peetsfea.type2_sampled import generate_sample_manifest_attempts

    seed = 19
    source_spec = load_type2_step_spec(TYPE2_SWEEP_TOML)
    owner_path, required_value, expected_retry = _single_retry_constraint_for_public_sampling(source_spec, seed=seed)
    toml_path = _write_toml_with_constraint(
        tmp_path,
        constraint_text=f"""
[[constraints.rules]]
id = "force_public_retry"
kind = "comparison"
message = "public sampling should retry until this sampled value appears"
lhs = {{ path = "{owner_path}" }}
op = "=="
rhs = {{ value = {required_value!r} }}
""",
        name="retry_type2.toml",
    )

    result = generate_sample_manifest_attempts(
        source_toml_path=toml_path,
        output_dir=tmp_path / "samples",
        seed_start=seed,
        count=1,
        jobs=1,
        make_step_on_sample=False,
    )

    assert result["skipped"] == []
    assert len(result["entries"]) == 1
    assert result["entries"][0]["retry_number"] >= expected_retry
    assert result["entries"][0]["retry_number"] > 0
