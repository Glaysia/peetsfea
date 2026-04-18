from __future__ import annotations

import hashlib
import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from peetsfea.spec.outputs import parse_outputs_table
from peetsfea.types.manifest import OutputsSpec

Point3 = tuple[float, float, float]
ModeledObjectRole = Literal["tx_single_coil", "rx_single_coil", "rx_plate_stack"]
_UNDERLAY_REPEAT_COUNT_CANDIDATES = (0, 2, 4, 6, 8)
_TX_UNDERLAY_GAP_MM_CANDIDATES = (1.0, 4.0, 7.0, 10.0)
_TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES = (0, 1)
_RX_PLATE_STACK_FERRITE_SET_COUNT = 10


@dataclass(frozen=True)
class RangeSpec:
    is_integer: bool
    start: float
    end: float
    count: int


@dataclass(frozen=True)
class NonModelBoxSpec:
    object_id: str
    kind: str
    primitive: Literal["box"]
    present: Literal[True]
    non_model: Literal[True]
    material: str
    plane: Literal["XY", "YZ", "ZX"]
    origin_xyz: Point3
    size_xyz: Point3


@dataclass(frozen=True)
class Type2SimulationPolicy:
    radiation_margin_mm: float


@dataclass(frozen=True)
class ModeledSingleCoilCommonSpec:
    object_id: str
    role: ModeledObjectRole
    material: str
    model_state: Literal[True]
    pcb_thickness_mm: float
    copper_thickness_mm: float
    outer_x_mm: RangeSpec
    outer_y_mm: RangeSpec
    turn_count: RangeSpec
    layer_count: RangeSpec
    underlay_repeat_count: RangeSpec
    layer_gap_mm: RangeSpec
    terminal_stub_length_mm: RangeSpec
    void_x_over_outer_x: RangeSpec
    void_y_over_outer_y: RangeSpec
    void_center_x_over_outer_x: RangeSpec
    void_center_y_over_outer_y: RangeSpec
    margin_ratio: RangeSpec
    metal_fill_factor: RangeSpec
    terminal_path: str


@dataclass(frozen=True)
class ModeledTxSingleCoilSpec(ModeledSingleCoilCommonSpec):
    role: Literal["tx_single_coil"]
    underlay_gap_mm: RangeSpec
    wall_parallel_stack_present: RangeSpec


@dataclass(frozen=True)
class ModeledRxSingleCoilSpec(ModeledSingleCoilCommonSpec):
    role: Literal["rx_single_coil"]


@dataclass(frozen=True)
class ModeledRxPlateStackSpec:
    object_id: str
    role: Literal["rx_plate_stack"]
    material: str
    model_state: Literal[True]
    pcb_total_thickness_mm: float
    copper_thickness_mm: float
    ferrite_set_count: int


ModeledSingleCoilSpec = ModeledTxSingleCoilSpec | ModeledRxSingleCoilSpec
ModeledObjectSpec = ModeledSingleCoilSpec | ModeledRxPlateStackSpec


@dataclass(frozen=True)
class Type2StepSpec:
    source_toml_path: str
    simulation: Type2SimulationPolicy
    outputs: OutputsSpec
    non_model_objects: tuple[NonModelBoxSpec, ...]
    modeled_objects: tuple[ModeledObjectSpec, ...]


def modeled_object_id_for_role(role: ModeledObjectRole) -> str:
    if role == "tx_single_coil":
        return "tx_rect_void_coil"
    if role == "rx_single_coil":
        return "rx_rect_void_coil"
    if role == "rx_plate_stack":
        return "rx_plate_stack"
    raise RuntimeError(f"unsupported modeled object role for object_id resolution: {role}")


def placement_owner_id_for_role(role: ModeledObjectRole) -> str:
    if role == "tx_single_coil":
        return "tx_region"
    if role in ("rx_single_coil", "rx_plate_stack"):
        return "rx_region_max"
    raise RuntimeError(f"unsupported modeled object role for placement owner resolution: {role}")


def modeled_plane_for_role(role: ModeledObjectRole) -> Literal["XY", "YZ"]:
    if role == "tx_single_coil":
        return "XY"
    if role in ("rx_single_coil", "rx_plate_stack"):
        return "YZ"
    raise RuntimeError(f"unsupported modeled object role for plane resolution: {role}")


def _require_key(table: dict[str, object], key: str, context: str) -> object:
    if key not in table:
        raise ValueError(f"{context} is missing required key '{key}'")
    return table[key]


def _require_table(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{context} must be a table")
    return cast(dict[str, object], value)


def _require_non_empty_str(table: dict[str, object], key: str, context: str) -> str:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, str):
        raise TypeError(f"{context}.{key} must be str")
    if raw_value == "":
        raise ValueError(f"{context}.{key} must be non-empty")
    return raw_value


def _require_true(table: dict[str, object], key: str, context: str) -> Literal[True]:
    raw_value = _require_key(table, key, context)
    if raw_value is not True:
        raise ValueError(f"{context}.{key} must be true")
    return True


def _require_float_value(table: dict[str, object], key: str, context: str) -> float:
    raw_value = _require_key(table, key, context)
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        raise TypeError(f"{context}.{key} must be number")
    return float(raw_value)


def _require_point3(table: dict[str, object], key: str, context: str, *, positive: bool) -> Point3:
    raw_value = _require_key(table, key, context)
    if not isinstance(raw_value, list):
        raise TypeError(f"{context}.{key} must be a list of three numbers")
    if len(raw_value) != 3:
        raise ValueError(f"{context}.{key} must contain exactly three numbers")
    parsed_values: list[float] = []
    for index, component in enumerate(raw_value):
        if isinstance(component, bool) or not isinstance(component, (int, float)):
            raise TypeError(f"{context}.{key}[{index}] must be numeric")
        value = float(component)
        if positive and value <= 0.0:
            raise ValueError(f"{context}.{key}[{index}] must be > 0")
        parsed_values.append(value)
    return (parsed_values[0], parsed_values[1], parsed_values[2])


def _require_plane(table: dict[str, object], key: str, context: str) -> Literal["XY", "YZ", "ZX"]:
    value = _require_non_empty_str(table, key, context)
    if value == "XY":
        return "XY"
    if value == "YZ":
        return "YZ"
    if value == "ZX":
        return "ZX"
    raise ValueError(f"{context}.{key} must be one of XY, YZ, ZX")


def _require_range(
    table: dict[str, object],
    key: str,
    context: str,
    *,
    expect_integer: bool,
) -> RangeSpec:
    raw_node = _require_key(table, key, context)
    node = _require_table(raw_node, f"{context}.{key}")
    if set(node.keys()) != {"range"}:
        raise ValueError(f"{context}.{key} must contain only ['range']")
    raw_range = node["range"]
    if not isinstance(raw_range, list):
        raise TypeError(f"{context}.{key}.range must be [is_integer, start, end, count]")
    if len(raw_range) != 4:
        raise ValueError(f"{context}.{key}.range must contain exactly four entries")
    raw_is_integer, raw_start, raw_end, raw_count = raw_range
    if not isinstance(raw_is_integer, bool):
        raise TypeError(f"{context}.{key}.range[0] must be bool")
    if raw_is_integer != expect_integer:
        expected = "true" if expect_integer else "false"
        raise ValueError(f"{context}.{key}.range[0] must be {expected}")
    if isinstance(raw_start, bool) or not isinstance(raw_start, (int, float)):
        raise TypeError(f"{context}.{key}.range[1] must be number")
    if isinstance(raw_end, bool) or not isinstance(raw_end, (int, float)):
        raise TypeError(f"{context}.{key}.range[2] must be number")
    if isinstance(raw_count, bool) or not isinstance(raw_count, int):
        raise TypeError(f"{context}.{key}.range[3] must be int")
    if raw_count < 1:
        raise ValueError(f"{context}.{key}.range[3] must be >= 1")
    start = float(raw_start)
    end = float(raw_end)
    if end < start:
        raise ValueError(f"{context}.{key}.range end must be >= start")
    return RangeSpec(is_integer=raw_is_integer, start=start, end=end, count=raw_count)


def _parse_simulation_policy(root: dict[str, object], *, context: str) -> Type2SimulationPolicy:
    simulation = _require_table(_require_key(root, "simulation", context), f"{context}.simulation")
    expected_keys = {"radiation_margin_mm"}
    missing_keys = sorted(expected_keys - set(simulation.keys()))
    if missing_keys:
        raise ValueError(f"{context}.simulation is missing required keys: {missing_keys}")
    extra_keys = sorted(set(simulation.keys()) - expected_keys)
    if extra_keys:
        raise ValueError(f"{context}.simulation contains unsupported keys: {extra_keys}")
    radiation_margin_mm = _require_float_value(simulation, "radiation_margin_mm", f"{context}.simulation")
    if radiation_margin_mm <= 0.0:
        raise ValueError(f"{context}.simulation.radiation_margin_mm must be > 0")
    return Type2SimulationPolicy(radiation_margin_mm=radiation_margin_mm)


def _parse_non_model_box(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> NonModelBoxSpec:
    context = f"non_model_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)

    primitive = _require_non_empty_str(table, "primitive", context)
    if primitive != "box":
        raise ValueError(f"{context}.primitive must be 'box'")

    return NonModelBoxSpec(
        object_id=object_id,
        kind=_require_non_empty_str(table, "kind", context),
        primitive="box",
        present=_require_true(table, "present", context),
        non_model=_require_true(table, "non_model", context),
        material=_require_non_empty_str(table, "material", context),
        plane=_require_plane(table, "plane", context),
        origin_xyz=_require_point3(table, "origin_xyz", context, positive=False),
        size_xyz=_require_point3(table, "size_xyz", context, positive=True),
    )


def _parse_modeled_single_coil(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> ModeledSingleCoilSpec:
    from peetsfea.tx_rect_void import profile_for_modeled_role

    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "object_id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)

    role = _require_non_empty_str(table, "role", context)
    if role not in ("tx_single_coil", "rx_single_coil"):
        raise ValueError(f"unsupported modeled object role: {role}")
    modeled_role = cast(Literal["tx_single_coil", "rx_single_coil"], role)
    profile = profile_for_modeled_role(modeled_role)
    if object_id != profile.object_id:
        raise ValueError(
            f"prototype modeled object_id must be '{profile.object_id}' for role {role} "
            f"(actual={object_id})"
        )

    raw_model_state = _require_key(table, "model_state", context)
    if not isinstance(raw_model_state, bool):
        raise TypeError(f"{context}.model_state must be bool")
    if raw_model_state is not True:
        raise ValueError(f"{context}.model_state must be true")

    pcb_thickness_mm = _require_float_value(table, "pcb_thickness_mm", context)
    if pcb_thickness_mm <= 0.0:
        raise ValueError(f"{context}.pcb_thickness_mm must be > 0")
    copper_thickness_mm = _require_float_value(table, "copper_thickness_mm", context)
    if copper_thickness_mm <= 0.0:
        raise ValueError(f"{context}.copper_thickness_mm must be > 0")
    material = _require_non_empty_str(table, "material", context)
    if material != "composite":
        raise ValueError(f"{context}.material must be 'composite' (actual={material})")

    terminal_node = _require_table(_require_key(table, "terminal_path", context), f"{context}.terminal_path")
    if set(terminal_node.keys()) != {"value"}:
        raise ValueError(f"{context}.terminal_path must contain only ['value']")
    terminal_path = _require_non_empty_str(terminal_node, "value", f"{context}.terminal_path")

    outer_x_mm = _require_range(table, "outer_x_mm", context, expect_integer=False)
    outer_y_mm = _require_range(table, "outer_y_mm", context, expect_integer=False)
    turn_count = _require_range(table, "turn_count", context, expect_integer=True)
    layer_count = _require_range(table, "layer_count", context, expect_integer=True)
    underlay_repeat_count = _require_underlay_repeat_count_range(
        table,
        context=context,
        role=modeled_role,
    )
    layer_gap_mm = _require_range(table, "layer_gap_mm", context, expect_integer=False)
    terminal_stub_length_mm = _require_range(table, "terminal_stub_length_mm", context, expect_integer=False)
    void_x_over_outer_x = _require_range(table, "void_x_over_outer_x", context, expect_integer=False)
    void_y_over_outer_y = _require_range(table, "void_y_over_outer_y", context, expect_integer=False)
    void_center_x_over_outer_x = _require_range(table, "void_center_x_over_outer_x", context, expect_integer=False)
    void_center_y_over_outer_y = _require_range(table, "void_center_y_over_outer_y", context, expect_integer=False)
    margin_ratio = _require_range(table, "margin_ratio", context, expect_integer=False)
    metal_fill_factor = _require_range(table, "metal_fill_factor", context, expect_integer=False)
    if modeled_role == "tx_single_coil":
        return ModeledTxSingleCoilSpec(
            object_id=object_id,
            role="tx_single_coil",
            material=material,
            model_state=True,
            pcb_thickness_mm=pcb_thickness_mm,
            copper_thickness_mm=copper_thickness_mm,
            outer_x_mm=outer_x_mm,
            outer_y_mm=outer_y_mm,
            turn_count=turn_count,
            layer_count=layer_count,
            underlay_repeat_count=underlay_repeat_count,
            layer_gap_mm=layer_gap_mm,
            terminal_stub_length_mm=terminal_stub_length_mm,
            void_x_over_outer_x=void_x_over_outer_x,
            void_y_over_outer_y=void_y_over_outer_y,
            void_center_x_over_outer_x=void_center_x_over_outer_x,
            void_center_y_over_outer_y=void_center_y_over_outer_y,
            margin_ratio=margin_ratio,
            metal_fill_factor=metal_fill_factor,
            terminal_path=terminal_path,
            underlay_gap_mm=_require_underlay_gap_range(table, context=context),
            wall_parallel_stack_present=_require_wall_parallel_stack_present_range(table, context=context),
        )
    if "underlay_gap_mm" in table:
        raise ValueError(f"{context}.underlay_gap_mm is unsupported for rx_single_coil")
    if "wall_parallel_stack_present" in table:
        raise ValueError(f"{context}.wall_parallel_stack_present is unsupported for rx_single_coil")
    return ModeledRxSingleCoilSpec(
        object_id=object_id,
        role="rx_single_coil",
        material=material,
        model_state=True,
        pcb_thickness_mm=pcb_thickness_mm,
        copper_thickness_mm=copper_thickness_mm,
        outer_x_mm=outer_x_mm,
        outer_y_mm=outer_y_mm,
        turn_count=turn_count,
        layer_count=layer_count,
        underlay_repeat_count=underlay_repeat_count,
        layer_gap_mm=layer_gap_mm,
        terminal_stub_length_mm=terminal_stub_length_mm,
        void_x_over_outer_x=void_x_over_outer_x,
        void_y_over_outer_y=void_y_over_outer_y,
        void_center_x_over_outer_x=void_center_x_over_outer_x,
        void_center_y_over_outer_y=void_center_y_over_outer_y,
        margin_ratio=margin_ratio,
        metal_fill_factor=metal_fill_factor,
        terminal_path=terminal_path,
    )


def _parse_modeled_rx_plate_stack(
    raw_object: object,
    *,
    index: int,
    seen_object_ids: set[str],
) -> ModeledRxPlateStackSpec:
    context = f"modeled_objects[{index}]"
    table = _require_table(raw_object, context)
    object_id = _require_non_empty_str(table, "object_id", context)
    if object_id in seen_object_ids:
        raise ValueError(f"duplicate object id: {object_id}")
    seen_object_ids.add(object_id)
    role = _require_non_empty_str(table, "role", context)
    if role != "rx_plate_stack":
        raise ValueError(f"unsupported modeled object role: {role}")
    expected_object_id = modeled_object_id_for_role("rx_plate_stack")
    if object_id != expected_object_id:
        raise ValueError(
            f"prototype modeled object_id must be '{expected_object_id}' for role {role} "
            f"(actual={object_id})"
        )
    raw_model_state = _require_key(table, "model_state", context)
    if not isinstance(raw_model_state, bool):
        raise TypeError(f"{context}.model_state must be bool")
    if raw_model_state is not True:
        raise ValueError(f"{context}.model_state must be true")
    material = _require_non_empty_str(table, "material", context)
    if material != "composite":
        raise ValueError(f"{context}.material must be 'composite' (actual={material})")
    pcb_total_thickness_mm = _require_float_value(table, "pcb_total_thickness_mm", context)
    if pcb_total_thickness_mm <= 0.0:
        raise ValueError(f"{context}.pcb_total_thickness_mm must be > 0")
    copper_thickness_mm = _require_float_value(table, "copper_thickness_mm", context)
    if copper_thickness_mm <= 0.0:
        raise ValueError(f"{context}.copper_thickness_mm must be > 0")
    if pcb_total_thickness_mm <= copper_thickness_mm:
        raise ValueError(
            f"{context}.pcb_total_thickness_mm must be > copper_thickness_mm "
            f"(pcb_total_thickness_mm={pcb_total_thickness_mm}, copper_thickness_mm={copper_thickness_mm})"
        )
    raw_ferrite_set_count = _require_key(table, "ferrite_set_count", context)
    if isinstance(raw_ferrite_set_count, bool) or not isinstance(raw_ferrite_set_count, int):
        raise TypeError(f"{context}.ferrite_set_count must be int")
    ferrite_set_count = raw_ferrite_set_count
    if ferrite_set_count != _RX_PLATE_STACK_FERRITE_SET_COUNT:
        raise ValueError(
            f"{context}.ferrite_set_count must be {_RX_PLATE_STACK_FERRITE_SET_COUNT} "
            f"(actual={ferrite_set_count})"
        )
    allowed_keys = {
        "object_id",
        "role",
        "material",
        "model_state",
        "pcb_total_thickness_mm",
        "copper_thickness_mm",
        "ferrite_set_count",
    }
    extra_keys = sorted(set(table.keys()) - allowed_keys)
    if extra_keys:
        raise ValueError(
            f"{context} contains unsupported keys for rx_plate_stack "
            f"(actual={extra_keys})"
        )
    return ModeledRxPlateStackSpec(
        object_id=object_id,
        role="rx_plate_stack",
        material=material,
        model_state=True,
        pcb_total_thickness_mm=pcb_total_thickness_mm,
        copper_thickness_mm=copper_thickness_mm,
        ferrite_set_count=ferrite_set_count,
    )


def _require_underlay_repeat_count_range(
    table: dict[str, object],
    *,
    context: str,
    role: ModeledObjectRole,
) -> RangeSpec:
    range_spec = _require_range(table, "underlay_repeat_count", context, expect_integer=True)
    if role not in ("tx_single_coil", "rx_single_coil"):
        raise RuntimeError(f"unsupported modeled object role for underlay_repeat_count validation: {role}")
    candidates = _integer_range_candidates(range_spec)
    if candidates == _UNDERLAY_REPEAT_COUNT_CANDIDATES:
        return range_spec
    if (
        range_spec.count == 1
        and range_spec.start == range_spec.end
        and len(candidates) == 1
        and candidates[0] in _UNDERLAY_REPEAT_COUNT_CANDIDATES
    ):
        return range_spec
    raise ValueError(
        f"{context}.underlay_repeat_count.range must be canonical [true, 0, 8, 5] "
        f"or fixed [true, n, n, 1] for n in {_UNDERLAY_REPEAT_COUNT_CANDIDATES} for {role} "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )
    return range_spec


def _require_underlay_gap_range(
    table: dict[str, object],
    *,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, "underlay_gap_mm", context, expect_integer=False)
    candidates = _float_range_candidates(range_spec)
    if candidates == _TX_UNDERLAY_GAP_MM_CANDIDATES:
        return range_spec
    if (
        range_spec.count == 1
        and range_spec.start == range_spec.end
        and len(candidates) == 1
        and candidates[0] in _TX_UNDERLAY_GAP_MM_CANDIDATES
    ):
        return range_spec
    raise ValueError(
        f"{context}.underlay_gap_mm.range must be canonical [false, 1.0, 10.0, 4] "
        f"or fixed [false, g, g, 1] for g in {_TX_UNDERLAY_GAP_MM_CANDIDATES} for tx_single_coil "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )
    return range_spec


def _require_wall_parallel_stack_present_range(
    table: dict[str, object],
    *,
    context: str,
) -> RangeSpec:
    range_spec = _require_range(table, "wall_parallel_stack_present", context, expect_integer=True)
    candidates = _integer_range_candidates(range_spec)
    if candidates == _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES:
        return range_spec
    if (
        range_spec.count == 1
        and range_spec.start == range_spec.end
        and len(candidates) == 1
        and candidates[0] in _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES
    ):
        return range_spec
    raise ValueError(
        f"{context}.wall_parallel_stack_present.range must be canonical [true, 0, 1, 2] "
        f"or fixed [true, b, b, 1] for b in {_TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES} for tx_single_coil "
        f"(actual={[range_spec.is_integer, range_spec.start, range_spec.end, range_spec.count]})"
    )


def _integer_range_candidates(range_spec: RangeSpec) -> tuple[int, ...]:
    if range_spec.is_integer is not True:
        raise ValueError("integer range candidates require integer range spec")
    if range_spec.count == 1:
        raw_values = (range_spec.start,)
    else:
        step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
        raw_values = tuple(range_spec.start + (step * index) for index in range(range_spec.count))
    rounded_values = tuple(int(math.floor(value + 0.5)) for value in raw_values)
    deduped_values: list[int] = []
    seen_values: set[int] = set()
    for value in rounded_values:
        if value in seen_values:
            continue
        seen_values.add(value)
        deduped_values.append(value)
    return tuple(deduped_values)


def _float_range_candidates(range_spec: RangeSpec) -> tuple[float, ...]:
    if range_spec.is_integer is not False:
        raise ValueError("float range candidates require non-integer range spec")
    if range_spec.count == 1:
        return (range_spec.start,)
    step = (range_spec.end - range_spec.start) / float(range_spec.count - 1)
    return tuple(range_spec.start + (step * index) for index in range(range_spec.count))


def _resolve_seeded_candidate_index(*, seed: int, range_path: str, candidate_count: int) -> int:
    digest = hashlib.blake2b(f"{seed}:{range_path}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False) % candidate_count


def resolve_modeled_underlay_repeat_count(spec: ModeledSingleCoilSpec, *, seed: int) -> int:
    candidates = _integer_range_candidates(spec.underlay_repeat_count)
    if spec.role not in ("tx_single_coil", "rx_single_coil"):
        raise RuntimeError(f"unsupported modeled object role for underlay repeat resolution: {spec.role}")
    if candidates != _UNDERLAY_REPEAT_COUNT_CANDIDATES and not (
        len(candidates) == 1 and candidates[0] in _UNDERLAY_REPEAT_COUNT_CANDIDATES
    ):
        raise ValueError(
            f"{spec.role}.underlay_repeat_count must realize to canonical candidates "
            f"{_UNDERLAY_REPEAT_COUNT_CANDIDATES} or a fixed single candidate from that set "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        repeat_count = candidates[0]
    else:
        range_path = f"modeled_objects.{spec.object_id}.underlay_repeat_count"
        index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
        repeat_count = candidates[index]
    return repeat_count


def resolve_modeled_underlay_gap_mm(spec: ModeledTxSingleCoilSpec, *, seed: int) -> float:
    candidates = _float_range_candidates(spec.underlay_gap_mm)
    if candidates != _TX_UNDERLAY_GAP_MM_CANDIDATES and not (
        len(candidates) == 1 and candidates[0] in _TX_UNDERLAY_GAP_MM_CANDIDATES
    ):
        raise ValueError(
            "tx_single_coil.underlay_gap_mm must realize to canonical candidates "
            f"{_TX_UNDERLAY_GAP_MM_CANDIDATES} or a fixed single candidate from that set "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        return candidates[0]
    range_path = f"modeled_objects.{spec.object_id}.underlay_gap_mm"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return candidates[index]


def resolve_modeled_wall_parallel_stack_present(spec: ModeledTxSingleCoilSpec, *, seed: int) -> bool:
    candidates = _integer_range_candidates(spec.wall_parallel_stack_present)
    if candidates != _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES and not (
        len(candidates) == 1 and candidates[0] in _TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES
    ):
        raise ValueError(
            "tx_single_coil.wall_parallel_stack_present must realize to canonical candidates "
            f"{_TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES} or a fixed single candidate from that set "
            f"(actual={candidates})"
        )
    if len(candidates) == 1:
        return bool(candidates[0])
    range_path = f"modeled_objects.{spec.object_id}.wall_parallel_stack_present"
    index = _resolve_seeded_candidate_index(seed=seed, range_path=range_path, candidate_count=len(candidates))
    return bool(candidates[index])


def load_type2_step_spec(toml_path: Path) -> Type2StepSpec:
    raw_text = toml_path.read_text(encoding="utf-8")
    raw_spec = tomllib.loads(raw_text)
    root = _require_table(raw_spec, toml_path.name)

    design = _require_table(_require_key(root, "design", toml_path.name), "design")
    units = _require_non_empty_str(design, "units", "design")
    if units != "mm":
        raise ValueError(f"design.units must be 'mm' (actual={units})")

    raw_non_model_objects = _require_key(root, "non_model_objects", toml_path.name)
    if not isinstance(raw_non_model_objects, list):
        raise TypeError("non_model_objects must be an array of tables")
    if len(raw_non_model_objects) == 0:
        raise ValueError("non_model_objects must not be empty")

    raw_modeled_objects = _require_key(root, "modeled_objects", toml_path.name)
    if not isinstance(raw_modeled_objects, list):
        raise TypeError("modeled_objects must be an array of tables")
    if len(raw_modeled_objects) == 0:
        raise ValueError("modeled_objects must not be empty")

    seen_object_ids: set[str] = set()
    non_model_objects = tuple(
        _parse_non_model_box(raw_object, index=index, seen_object_ids=seen_object_ids)
        for index, raw_object in enumerate(raw_non_model_objects)
    )
    modeled_objects_list: list[ModeledObjectSpec] = []
    for index, raw_object in enumerate(raw_modeled_objects):
        context = f"{toml_path.name}.modeled_objects[{index}]"
        table = _require_table(raw_object, context)
        role = _require_non_empty_str(table, "role", context)
        if role == "rx_plate_stack":
            modeled_objects_list.append(
                _parse_modeled_rx_plate_stack(raw_object, index=index, seen_object_ids=seen_object_ids)
            )
            continue
        modeled_objects_list.append(
            _parse_modeled_single_coil(raw_object, index=index, seen_object_ids=seen_object_ids)
        )
    modeled_objects = tuple(modeled_objects_list)
    return Type2StepSpec(
        source_toml_path=str(toml_path),
        simulation=_parse_simulation_policy(root, context=toml_path.name),
        outputs=parse_outputs_table(_require_key(root, "outputs", toml_path.name), context=f"{toml_path.name}.outputs"),
        non_model_objects=non_model_objects,
        modeled_objects=modeled_objects,
    )


def _format_range(range_spec: RangeSpec) -> str:
    is_integer = "true" if range_spec.is_integer else "false"
    return f"[{is_integer}, {range_spec.start}, {range_spec.end}, {range_spec.count}]"


def render_tx_rect_void_toml(spec: ModeledSingleCoilCommonSpec) -> str:
    return "\n".join(
        (
            'spec_version = "0.2.22"',
            'schema_id = "peetsfea.tx_rect_void_coil.step.v1"',
            "runtime_compatible = false",
            "",
            "[design]",
            'units = "mm"',
            "",
            "[manufacturing]",
            f"pcb_thickness_mm = {spec.pcb_thickness_mm}",
            f"copper_thickness_mm = {spec.copper_thickness_mm}",
            "",
            "[tx_coil.outer_x_mm]",
            f"range = {_format_range(spec.outer_x_mm)}",
            "[tx_coil.outer_y_mm]",
            f"range = {_format_range(spec.outer_y_mm)}",
            "[tx_coil.turn_count]",
            f"range = {_format_range(spec.turn_count)}",
            "[tx_coil.layer_count]",
            f"range = {_format_range(spec.layer_count)}",
            "[tx_coil.layer_gap_mm]",
            f"range = {_format_range(spec.layer_gap_mm)}",
            "[tx_coil.terminal_stub_length_mm]",
            f"range = {_format_range(spec.terminal_stub_length_mm)}",
            "[tx_coil.void_x_over_outer_x]",
            f"range = {_format_range(spec.void_x_over_outer_x)}",
            "[tx_coil.void_y_over_outer_y]",
            f"range = {_format_range(spec.void_y_over_outer_y)}",
            "[tx_coil.void_center_x_over_outer_x]",
            f"range = {_format_range(spec.void_center_x_over_outer_x)}",
            "[tx_coil.void_center_y_over_outer_y]",
            f"range = {_format_range(spec.void_center_y_over_outer_y)}",
            "[tx_coil.margin_ratio]",
            f"range = {_format_range(spec.margin_ratio)}",
            "[tx_coil.metal_fill_factor]",
            f"range = {_format_range(spec.metal_fill_factor)}",
            "[tx_coil.terminal_path]",
            f'value = "{spec.terminal_path}"',
            "",
        )
    )


__all__ = [
    "ModeledObjectSpec",
    "ModeledObjectRole",
    "ModeledRxPlateStackSpec",
    "ModeledRxSingleCoilSpec",
    "ModeledSingleCoilCommonSpec",
    "ModeledSingleCoilSpec",
    "ModeledTxSingleCoilSpec",
    "NonModelBoxSpec",
    "Point3",
    "RangeSpec",
    "Type2SimulationPolicy",
    "Type2StepSpec",
    "load_type2_step_spec",
    "modeled_object_id_for_role",
    "modeled_plane_for_role",
    "placement_owner_id_for_role",
    "resolve_modeled_underlay_gap_mm",
    "resolve_modeled_underlay_repeat_count",
    "resolve_modeled_wall_parallel_stack_present",
    "render_tx_rect_void_toml",
]
