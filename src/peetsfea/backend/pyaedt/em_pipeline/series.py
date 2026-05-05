from __future__ import annotations


def build_series(groups: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        "tx": list(groups.get("tx", [])),
        "rx": list(groups.get("rx", [])),
    }
