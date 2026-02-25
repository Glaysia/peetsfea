from __future__ import annotations

from typing import Literal, TypedDict, TypeAlias


Number: TypeAlias = int | float
SamplingContext: TypeAlias = dict[str, Number]
PcbMountSpec: TypeAlias = tuple[Literal["tx_dd", "tx_vertical", "rx_dd"], Literal["all", "index"], int | None]
GroupKind: TypeAlias = Literal["tx_dd", "tx_vertical", "rx_dd"]


class SelectionConstraintError(ValueError):
    pass


class PathRef(TypedDict):
    path: str


class ValueRef(TypedDict):
    value: float | str


class FuncRef(TypedDict):
    func: str


ComparableRef: TypeAlias = PathRef | FuncRef
OperandRef: TypeAlias = PathRef | ValueRef | FuncRef


class ComparisonRule(TypedDict):
    id: str
    kind: Literal["comparison"]
    message: str
    enabled: bool
    lhs: ComparableRef
    op: Literal["<", "<=", ">", ">=", "=="]
    rhs: OperandRef


class RangeRule(TypedDict):
    id: str
    kind: Literal["range"]
    message: str
    enabled: bool
    target: PathRef
    min: ValueRef | None
    max: ValueRef | None
    inclusive_min: bool
    inclusive_max: bool


class AggregateRule(TypedDict):
    id: str
    kind: Literal["aggregate"]
    message: str
    enabled: bool
    agg: Literal["sum_group_selected_count"]
    op: Literal["<", "<=", ">", ">=", "=="]
    rhs: ValueRef


ConstraintRule: TypeAlias = ComparisonRule | RangeRule | AggregateRule


class _FixedPcbRule(TypedDict):
    role: Literal["tx", "rx"]
    present: bool
    mounts: tuple[PcbMountSpec, ...]
