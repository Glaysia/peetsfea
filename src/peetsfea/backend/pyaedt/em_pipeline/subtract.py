from __future__ import annotations


def build_subtract(groups: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        "tool": list(groups.get("tx", []) + groups.get("rx", [])),
        "blank": list(groups.get("fr4", [])),
    }
