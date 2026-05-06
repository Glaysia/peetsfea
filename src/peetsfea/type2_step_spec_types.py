from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias, TypedDict

from peetsfea.types.manifest import OutputsSpec

Point3 = tuple[float, float, float]


ModeledSingleCoilRole = Literal["tx_single_coil", "tx_inner_single_coil", "rx_single_coil"]
ModeledPlateStackRole = Literal["tx_plate_stack", "rx_plate_stack"]
ModeledObjectRole = Literal[
    "tx_single_coil",
    "tx_inner_single_coil",
    "rx_single_coil",
    "tx_rect_void_columns",
    "tx_plate_stack",
    "rx_plate_stack",
    "tv_aluminum_plate",
]
_UNDERLAY_REPEAT_COUNT_CANDIDATES = (0, 2, 4, 6, 8)
_UNDERLAY_REPEAT_COUNT_FIXED_CANDIDATES = (0, 1, 2, 4, 6, 8)
_TX_UNDERLAY_GAP_MM_CANDIDATES = (1.0, 4.0, 7.0, 10.0)
_TX_WALL_PARALLEL_STACK_PRESENT_CANDIDATES = (0, 1)
_TX_INNER_VOID_STACK_PRESENT_CANDIDATES = (0, 1)
_TX_PLATE_STACK_COIL_COUNT_CANDIDATES = (1, 2, 3, 4)
_TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_START = 0.1
_TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_END = 0.6
_TX_PLATE_STACK_ARRAY_X_USAGE_RATIO_COUNT = 14
_TX_REGION_ACTUAL_USAGE_RATIO_START = 0.3
_TX_REGION_ACTUAL_USAGE_RATIO_END = 1.0
_TX_REGION_ACTUAL_USAGE_RATIO_COUNT = 27
_TX_REGION_ACTUAL_DIVISION_COUNT_START = 1
_TX_REGION_ACTUAL_DIVISION_COUNT_END = 3
_TX_REGION_ACTUAL_DIVISION_COUNT_COUNT = 3
_TX_REGION_ACTUAL_DIVISION_COUNT_VALUES = (1, 2, 3)
_TX_REGION_ACTUAL_STACK_SPACE_TILT_ENABLED_VALUE = 1
_TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_START = 0.35
_TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_END = 0.95
_TX_REGION_ACTUAL_STACK_SPACE_SCALE_RATIO_COUNT = 25
_TX_REGION_ACTUAL_STACK_SPACE_TOTAL_THICKNESS_MM = 5.0
_TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_START = 1
_TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_END = 4
_TX_RECT_VOID_COLUMNS_LAYER_COUNT_RANGE_COUNT = 4
_TX_RECT_VOID_COLUMNS_LAYER_COUNT_ALLOWED = (1, 2, 3, 4)
_TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_START = 1.0
_TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_END = 1.8
_TX_RECT_VOID_COLUMNS_LAYER_GAP_MM_RANGE_COUNT = 5
_TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_START = 10.0
_TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_END = 10.0
_TX_RECT_VOID_COLUMNS_TERMINAL_STUB_LENGTH_MM_RANGE_COUNT = 1
_TX_RECT_VOID_COLUMNS_CONNECTION_MODE_EXPECTED = (0, 1)
_TX_RECT_VOID_COLUMNS_CONNECTION_MODE_RANGE = (0, 1, 2)
_TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_START = 0.1111111111111111
_TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_END = 31.0
_TX_RECT_VOID_COLUMNS_EQUIVALENT_TURN_COUNT_RANGE_COUNT = 100
_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_A_RANGE_START = 0.5
_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_A_RANGE_END = 1.5
_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_A_RANGE_COUNT = 5
_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_B_RANGE_START = -0.5
_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_B_RANGE_END = 0.5
_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_B_RANGE_COUNT = 21
_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_C_RANGE_START = -0.3
_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_C_RANGE_END = 0.3
_TX_RECT_VOID_COLUMNS_TURN_WEIGHT_C_RANGE_COUNT = 21
_TYPE2_SCHEMA_ID = "peetsfea.type2.step.v8"


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
class NonModelTxReferenceLineSpec:
    x_ratio: RangeSpec
    y_usage_ratio: RangeSpec
    z_ratio: RangeSpec


@dataclass(frozen=True)
class NonModelTxRegionSpec(NonModelBoxSpec):
    object_id: Literal["tx_region"]
    kind: Literal["tx_region"]
    tx_reference_line: NonModelTxReferenceLineSpec


@dataclass(frozen=True)
class NonModelTxRegionActualSpec:
    object_id: Literal["tx_region_actual"]
    kind: Literal["tx_region_actual"]
    source_region_id: Literal["tx_region"]
    x_usage_ratio: RangeSpec
    y_usage_ratio: RangeSpec
    x_division_count: RangeSpec
    y_division_count: RangeSpec


@dataclass(frozen=True)
class NonModelTxRegionActualStackSpaceSpec:
    object_id: Literal["tx_region_actual_stack_space"]
    kind: Literal["tx_region_actual_stack_space"]
    source_region_id: Literal["tx_region_actual"]
    total_thickness_mm: float
    tilt_enabled: RangeSpec
    scale_ratio: RangeSpec


NonModelDerivedSpec: TypeAlias = NonModelTxRegionActualSpec | NonModelTxRegionActualStackSpaceSpec


@dataclass(frozen=True)
class Type2SimulationPolicy:
    radiation_margin_mm: float


Type2ConstraintComparisonOperator = Literal["<", "<=", ">", ">=", "=="]


class Type2ConstraintPathRef(TypedDict):
    path: str


class Type2ConstraintValueRef(TypedDict):
    value: str | float


class Type2ConstraintFuncRef(TypedDict):
    func: str


Type2ConstraintComparableRef = Type2ConstraintPathRef | Type2ConstraintFuncRef
Type2ConstraintOperandRef = Type2ConstraintPathRef | Type2ConstraintValueRef | Type2ConstraintFuncRef


@dataclass(frozen=True)
class Type2ConstraintRule:
    id: str
    message: str
    enabled: bool
    lhs: Type2ConstraintComparableRef
    op: Type2ConstraintComparisonOperator
    rhs: Type2ConstraintOperandRef


@dataclass(frozen=True)
class ModeledSingleCoilCommonSpec:
    object_id: str
    role: ModeledSingleCoilRole
    material: str
    model_state: Literal[True]
    pcb_thickness_mm: float
    copper_thickness_mm: float
    outer_x_usage_ratio: RangeSpec
    outer_y_usage_ratio: RangeSpec
    x_position_ratio: RangeSpec
    outer_x_mm: RangeSpec
    outer_y_mm: RangeSpec
    turn_count: RangeSpec
    layer_count: RangeSpec
    underlay_repeat_count: RangeSpec
    layer_gap_mm: RangeSpec
    terminal_stub_length_mm: RangeSpec
    void_usage_ratio: RangeSpec
    margin_ratio: RangeSpec
    metal_fill_factor: RangeSpec
    terminal_path: str


@dataclass(frozen=True)
class ModeledTxSingleCoilSpec(ModeledSingleCoilCommonSpec):
    role: Literal["tx_single_coil"]
    underlay_gap_mm: RangeSpec
    wall_parallel_stack_present: RangeSpec


@dataclass(frozen=True)
class ModeledTxInnerSingleCoilSpec(ModeledSingleCoilCommonSpec):
    role: Literal["tx_inner_single_coil"]
    void_stack_present: RangeSpec
    underlay_pet_psa_thickness_mm: RangeSpec
    underlay_ferrite_thickness_mm: RangeSpec


@dataclass(frozen=True)
class ModeledRxSingleCoilSpec(ModeledSingleCoilCommonSpec):
    role: Literal["rx_single_coil"]


@dataclass(frozen=True)
class ModeledPlateStackCommonSpec:
    object_id: str
    role: ModeledPlateStackRole
    material: str
    model_state: Literal[True]
    pcb_total_thickness_mm: float
    copper_thickness_mm: float
    turn_count: RangeSpec
    metal_fill_factor: RangeSpec
    z_usage_ratio: RangeSpec
    y_usage_ratio: RangeSpec


@dataclass(frozen=True)
class ModeledTxPlateStackSpec(ModeledPlateStackCommonSpec):
    role: Literal["tx_plate_stack"]
    tx_coil_count: RangeSpec
    tx_array_x_usage_ratio: RangeSpec


@dataclass(frozen=True)
class ModeledRxPlateStackSpec(ModeledPlateStackCommonSpec):
    role: Literal["rx_plate_stack"]


@dataclass(frozen=True)
class ModeledTxRectVoidColumnsSpec:
    object_id: str
    role: Literal["tx_rect_void_columns"]
    material: str
    model_state: Literal[True]
    pcb_thickness_mm: float
    copper_thickness_mm: float
    layer_count: RangeSpec
    layer_gap_mm: RangeSpec
    terminal_stub_length_mm: RangeSpec
    void_usage_ratio: RangeSpec
    margin_ratio: RangeSpec
    metal_fill_factor: RangeSpec
    terminal_path: str
    connection_mode: RangeSpec
    equivalent_turn_count: RangeSpec
    turn_weight_a: RangeSpec
    turn_weight_b: RangeSpec
    turn_weight_c: RangeSpec


@dataclass(frozen=True)
class ModeledTvAluminumPlateSpec:
    object_id: str
    role: Literal["tv_aluminum_plate"]
    primitive: Literal["box"]
    material: Literal["aluminum"]
    model_state: Literal[True]
    source_non_model_object_id: str
    face: Literal["+x"]
    thickness_mm: float


ModeledSingleCoilSpec = ModeledTxSingleCoilSpec | ModeledTxInnerSingleCoilSpec | ModeledRxSingleCoilSpec
ModeledPlateStackSpec = ModeledTxPlateStackSpec | ModeledRxPlateStackSpec
ModeledObjectSpec = (
    ModeledSingleCoilSpec | ModeledPlateStackSpec | ModeledTxRectVoidColumnsSpec | ModeledTvAluminumPlateSpec
)


@dataclass(frozen=True)
class Type2StepSpec:
    source_toml_path: str
    simulation: Type2SimulationPolicy
    outputs: OutputsSpec
    non_model_objects: tuple[NonModelBoxSpec, ...]
    non_model_derived_objects: tuple[NonModelDerivedSpec, ...]
    modeled_objects: tuple[ModeledObjectSpec, ...]
    constraints: tuple[Type2ConstraintRule, ...]


def modeled_object_id_for_role(role: ModeledObjectRole) -> str:
    if role == "tx_single_coil":
        return "tx_rect_void_coil"
    if role == "tx_inner_single_coil":
        return "tx_inner_rect_void_coil"
    if role == "rx_single_coil":
        return "rx_rect_void_coil"
    if role == "tx_rect_void_columns":
        return "tx_rect_void_columns"
    if role == "tx_plate_stack":
        return "tx_plate_stack"
    if role == "rx_plate_stack":
        return "rx_plate_stack"
    if role == "tv_aluminum_plate":
        return "tv_aluminum_plate"
    raise RuntimeError(f"unsupported modeled object role for object_id resolution: {role}")


def placement_owner_id_for_role(role: ModeledObjectRole) -> str:
    if role in ("tx_single_coil", "tx_rect_void_columns", "tx_plate_stack"):
        return "tx_region"
    if role == "tx_inner_single_coil":
        return "tx_inner_region"
    if role in ("rx_single_coil", "rx_plate_stack"):
        return "rx_region_max"
    if role == "tv_aluminum_plate":
        return "tv"
    raise RuntimeError(f"unsupported modeled object role for placement owner resolution: {role}")


def modeled_plane_for_role(role: ModeledObjectRole) -> Literal["XY", "YZ"]:
    if role in ("tx_single_coil", "tx_inner_single_coil"):
        return "XY"
    if role == "tx_rect_void_columns":
        return "XY"
    if role == "tx_plate_stack":
        return "YZ"
    if role in ("rx_single_coil", "rx_plate_stack"):
        return "YZ"
    if role == "tv_aluminum_plate":
        return "YZ"
    raise RuntimeError(f"unsupported modeled object role for plane resolution: {role}")


__all__ = [
    "ModeledObjectRole",
    "ModeledPlateStackRole",
    "ModeledPlateStackSpec",
    "ModeledRxPlateStackSpec",
    "ModeledRxSingleCoilSpec",
    "ModeledSingleCoilRole",
    "ModeledSingleCoilCommonSpec",
    "ModeledSingleCoilSpec",
    "ModeledTxPlateStackSpec",
    "ModeledTxRectVoidColumnsSpec",
    "ModeledTxInnerSingleCoilSpec",
    "ModeledTxSingleCoilSpec",
    "ModeledTvAluminumPlateSpec",
    "NonModelBoxSpec",
    "NonModelDerivedSpec",
    "NonModelTxReferenceLineSpec",
    "NonModelTxRegionSpec",
    "NonModelTxRegionActualSpec",
    "NonModelTxRegionActualStackSpaceSpec",
    "Point3",
    "RangeSpec",
    "Type2ConstraintComparisonOperator",
    "Type2ConstraintComparableRef",
    "Type2ConstraintFuncRef",
    "Type2ConstraintOperandRef",
    "Type2ConstraintPathRef",
    "Type2ConstraintRule",
    "Type2ConstraintValueRef",
    "Type2SimulationPolicy",
    "Type2StepSpec",
    "modeled_object_id_for_role",
    "modeled_plane_for_role",
    "placement_owner_id_for_role",
]
