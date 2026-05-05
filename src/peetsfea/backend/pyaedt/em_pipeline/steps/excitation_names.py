from __future__ import annotations


def normalize_excitation_name(name: str) -> str:
    return str(name).strip().strip("'\"").lstrip("(").rstrip(")")


def normalized_excitation_name_map(excitation_names: list[str]) -> dict[str, str]:
    normalized_map: dict[str, str] = {}
    for raw_name in excitation_names:
        normalized_name = normalize_excitation_name(raw_name)
        if normalized_name:
            normalized_map[normalized_name] = raw_name
    return normalized_map
