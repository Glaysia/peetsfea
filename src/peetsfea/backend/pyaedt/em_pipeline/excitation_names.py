from __future__ import annotations

import re

from peetsfea.types.manifest import GroupEndpointEntry

_RX_STUB_EXCITATION_REGEX = re.compile(r"^rxs_(?P<board_id>.+)_(?P<instance_index>\d+)_(?P<label>[A-Za-z])_T1$")
_RX_CANONICAL_REFERENCE_LABEL = "c"


def normalize_excitation_name(name: str) -> str:
    return str(name).strip().strip("'\"").lstrip("(").rstrip(")")


def normalized_excitation_name_map(excitation_names: list[str]) -> dict[str, str]:
    normalized_map: dict[str, str] = {}
    for raw_name in excitation_names:
        normalized_name = normalize_excitation_name(raw_name)
        if normalized_name:
            normalized_map[normalized_name] = raw_name
    return normalized_map


def select_regex_fallback_name(
    *,
    excitation_names: list[str],
    regex_fallback: str,
    prefer_canonical_rx_stub: bool = False,
) -> str | None:
    normalized_map = normalized_excitation_name_map(excitation_names)
    matched_names = [normalized_name for normalized_name in normalized_map if re.search(regex_fallback, normalized_name)]
    if not matched_names:
        return None
    selected_name = sorted(
        matched_names,
        key=_rx_stub_fallback_sort_key if prefer_canonical_rx_stub else _default_excitation_sort_key,
    )[0]
    return normalized_map[selected_name]


def build_rx_port_preferred_names(endpoints: list[GroupEndpointEntry]) -> list[str]:
    if not endpoints:
        return []
    preferred_names = ["RX_TML"]
    canonical_stub_names = sorted(
        {
            f"rxs_{entry['board_id']}_{entry['group_instance_index']}_{_RX_CANONICAL_REFERENCE_LABEL}_T1"
            for entry in endpoints
            if entry["group_kind"] == "rx_dd"
            and entry["present"]
            and (
                entry["start_label"] == _RX_CANONICAL_REFERENCE_LABEL
                or entry["end_label"] == _RX_CANONICAL_REFERENCE_LABEL
            )
        }
    )
    preferred_names.extend(canonical_stub_names)
    return preferred_names


def _default_excitation_sort_key(normalized_name: str) -> str:
    return normalized_name


def _rx_stub_fallback_sort_key(normalized_name: str) -> tuple[int, str]:
    match = _RX_STUB_EXCITATION_REGEX.fullmatch(normalized_name)
    if match is None:
        return (1, normalized_name)
    label = match.group("label")
    return (0 if label == _RX_CANONICAL_REFERENCE_LABEL else 1, normalized_name)
