from __future__ import annotations

from typing import Final, Literal, TypedDict, cast

Type2SampleSkipPhase = Literal["sample", "step"]
Type2SampleSkippableException = ValueError | RuntimeError


class Type2SampleSkippedEntry(TypedDict):
    seed: int
    sample_index: int
    phase: Type2SampleSkipPhase
    error_type: str
    error_message: str


_SKIP_PHASES: Final[tuple[Type2SampleSkipPhase, ...]] = ("sample", "step")


def _require_int(value: object, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{context} must be int")
    return value


def _require_non_empty_str(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be str")
    if value == "":
        raise ValueError(f"{context} must be non-empty")
    return value


def _require_phase(value: object, *, context: str) -> Type2SampleSkipPhase:
    phase = _require_non_empty_str(value, context=context)
    if phase not in _SKIP_PHASES:
        raise ValueError(f"{context} must be one of {_SKIP_PHASES}")
    return cast(Type2SampleSkipPhase, phase)


def build_type2_sample_skipped_entry(
    *,
    seed: int,
    sample_index: int,
    phase: Type2SampleSkipPhase,
    exc: Type2SampleSkippableException,
) -> Type2SampleSkippedEntry:
    if not isinstance(exc, (ValueError, RuntimeError)):
        raise TypeError("exc must be ValueError or RuntimeError")
    return {
        "seed": _require_int(seed, context="seed"),
        "sample_index": _require_int(sample_index, context="sample_index"),
        "phase": _require_phase(phase, context="phase"),
        "error_type": _require_non_empty_str(type(exc).__name__, context="error_type"),
        "error_message": _require_non_empty_str(str(exc), context="error_message"),
    }


def _load_type2_sample_skipped_entry(raw_entry: object, *, index: int) -> Type2SampleSkippedEntry:
    if not isinstance(raw_entry, dict):
        raise TypeError(f"skipped entries[{index}] must be a table/object")
    required_fields = (
        "seed",
        "sample_index",
        "phase",
        "error_type",
        "error_message",
    )
    for field_name in required_fields:
        if field_name not in raw_entry:
            raise ValueError(f"skipped entries[{index}] is missing required key {field_name!r}")
    return {
        "seed": _require_int(raw_entry["seed"], context=f"skipped entries[{index}].seed"),
        "sample_index": _require_int(raw_entry["sample_index"], context=f"skipped entries[{index}].sample_index"),
        "phase": _require_phase(raw_entry["phase"], context=f"skipped entries[{index}].phase"),
        "error_type": _require_non_empty_str(raw_entry["error_type"], context=f"skipped entries[{index}].error_type"),
        "error_message": _require_non_empty_str(raw_entry["error_message"], context=f"skipped entries[{index}].error_message"),
    }


def copy_type2_sample_skipped_entries(
    entries: list[Type2SampleSkippedEntry],
) -> list[Type2SampleSkippedEntry]:
    copies: list[Type2SampleSkippedEntry] = []
    for index, raw_entry in enumerate(entries):
        copied = _load_type2_sample_skipped_entry(raw_entry, index=index)
        copies.append(copied)
    return copies


def load_type2_sample_skipped_entries(raw_entries: object) -> list[Type2SampleSkippedEntry]:
    if not isinstance(raw_entries, list):
        raise TypeError("skipped entries must be a list")
    copied: list[Type2SampleSkippedEntry] = []
    for index, raw_entry in enumerate(raw_entries):
        copied.append(_load_type2_sample_skipped_entry(raw_entry, index=index))
    return copied
