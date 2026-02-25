from __future__ import annotations

import math
from typing import Sequence

from peetsfea.spec.loader import TOMLTable, TOMLValue, require_table

from .constants import ATTEMPT_STRIDE, DERIVED_RANGE_PATHS
from .path_access import read_path, read_range_definition
from .types import Number, SamplingContext


def is_dummy_derived_range(raw_range: list[TOMLValue]) -> bool:
    if len(raw_range) != 4:
        return False
    is_integer, start, end, count = raw_range
    return (
        isinstance(is_integer, bool)
        and is_integer is False
        and isinstance(start, (int, float))
        and not isinstance(start, bool)
        and float(start) == -1.0
        and isinstance(end, (int, float))
        and not isinstance(end, bool)
        and float(end) == -1.0
        and isinstance(count, int)
        and not isinstance(count, bool)
        and count == -1
    )


def ensure_dummy_derived_range(raw_range: list[TOMLValue], dotted_path: str) -> None:
    if not is_dummy_derived_range(raw_range):
        raise ValueError(f"{dotted_path}.range for derived path must be exactly [false, -1, -1, -1]")


def parse_range_at_path(root: TOMLTable, dotted_path: str, expect_integer: bool) -> tuple[bool, float, float, int]:
    table = require_table(read_path(root, dotted_path), dotted_path)
    if set(table.keys()) != {"range"}:
        raise ValueError(f"{dotted_path} supports only the 'range' key")

    raw_range = table.get("range")
    if not isinstance(raw_range, list) or len(raw_range) != 4:
        raise ValueError(f"{dotted_path}.range must be [is_integer, start, end, count]")
    is_integer, start, end, count = raw_range

    if not isinstance(is_integer, bool):
        raise ValueError(f"{dotted_path}.range[0] (is_integer) must be bool")
    if isinstance(start, bool) or not isinstance(start, (int, float)):
        raise ValueError(f"{dotted_path}.range[1] (start) must be number")
    if isinstance(end, bool) or not isinstance(end, (int, float)):
        raise ValueError(f"{dotted_path}.range[2] (end) must be number")
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError(f"{dotted_path}.range[3] (count) must be int")
    if count < 1:
        raise ValueError(f"{dotted_path}.range[3] (count) must be >= 1")
    if end < start:
        raise ValueError(f"{dotted_path}.range[2] (end) must be >= range[1] (start)")
    if is_integer != expect_integer:
        expected = "true" if expect_integer else "false"
        raise ValueError(f"{dotted_path}.range[0] (is_integer) must be {expected}")
    return is_integer, float(start), float(end), count


def build_candidates(is_integer: bool, start: float, end: float, count: int) -> Sequence[Number]:
    raw_values: list[float]
    if count == 1:
        raw_values = [start]
    else:
        step = (end - start) / float(count - 1)
        raw_values = [start + (step * i) for i in range(count)]

    if not is_integer:
        return tuple(raw_values)

    rounded = [int(math.floor(value + 0.5)) for value in raw_values]
    deduped: list[Number] = []
    seen: set[int] = set()
    for value in rounded:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return tuple(deduped)


def sample_candidate(candidates: Sequence[Number], *, seed: int, offset: int, attempt: int) -> Number:
    if len(candidates) == 0:
        raise ValueError("No candidates available for sampling")
    return candidates[(seed + offset + (attempt * ATTEMPT_STRIDE)) % len(candidates)]


def select_range_value(
    root: TOMLTable,
    dotted_path: str,
    expect_integer: bool,
    seed: int,
    offset: int,
    attempt: int,
    context: SamplingContext,
) -> Number:
    if dotted_path in context:
        return context[dotted_path]
    raw_range = read_range_definition(root, dotted_path)
    if dotted_path in DERIVED_RANGE_PATHS:
        ensure_dummy_derived_range(raw_range, dotted_path)
        derived_from_path = DERIVED_RANGE_PATHS[dotted_path]
        selected = select_range_value(
            root,
            derived_from_path,
            expect_integer=expect_integer,
            seed=seed,
            offset=offset,
            attempt=attempt,
            context=context,
        )
        context[dotted_path] = selected
        return selected
    if is_dummy_derived_range(raw_range):
        raise ValueError(
            f"{dotted_path}.range uses reserved derived marker [false, -1, -1, -1] "
            "but this path is not declared as derived"
        )
    is_integer, start, end, count = parse_range_at_path(root, dotted_path, expect_integer=expect_integer)
    candidates = build_candidates(is_integer=is_integer, start=start, end=end, count=count)
    if len(candidates) == 0:
        raise ValueError(f"No candidates generated from {dotted_path}.range")
    selected = sample_candidate(candidates, seed=seed, offset=offset, attempt=attempt)
    context[dotted_path] = selected
    return selected


def select_range_end_value(root: TOMLTable, dotted_path: str, expect_integer: bool) -> Number:
    raw_range = read_range_definition(root, dotted_path)
    if dotted_path in DERIVED_RANGE_PATHS:
        ensure_dummy_derived_range(raw_range, dotted_path)
        return select_range_end_value(root, DERIVED_RANGE_PATHS[dotted_path], expect_integer=expect_integer)
    if is_dummy_derived_range(raw_range):
        raise ValueError(
            f"{dotted_path}.range uses reserved derived marker [false, -1, -1, -1] "
            "but this path is not declared as derived"
        )
    is_integer, _, end, _ = parse_range_at_path(root, dotted_path, expect_integer=expect_integer)
    if is_integer:
        return int(math.floor(end + 0.5))
    return float(end)
