from __future__ import annotations

import re
from typing import Protocol, cast

from ansys.aedt.core import Hfss


class _SolutionsModule(Protocol):
    def EditSources(self, payload: list[object]) -> None: ...


class _DesignModuleProvider(Protocol):
    def GetModule(self, name: str) -> object: ...


def _normalize_excitation_name(name: str) -> str:
    return str(name).strip().strip("'\"").lstrip("(").rstrip(")")


def _find_excitation_name(
    *,
    preferred_names: list[str],
    excitation_names: list[str],
    exact_fallback: str,
    regex_fallback: str,
    role: str,
) -> str:
    normalized_map: dict[str, str] = {_normalize_excitation_name(raw): raw for raw in excitation_names}
    for preferred in preferred_names:
        normalized_preferred = _normalize_excitation_name(preferred)
        if not excitation_names and normalized_preferred:
            return preferred
        if normalized_preferred in normalized_map:
            return normalized_map[normalized_preferred]

    if exact_fallback in normalized_map:
        return normalized_map[exact_fallback]
    for normalized, raw in normalized_map.items():
        if re.search(regex_fallback, normalized):
            return raw
    raise ValueError(f"Could not resolve {role} source excitation name from available excitations: {sorted(normalized_map)}")


def apply_sources_phase(hfss: Hfss, ports: dict[str, list[str]]) -> dict[str, str]:
    design = hfss.odesign
    assert design is not None and not isinstance(design, str), "HFSS design is not initialized"
    solutions = cast(_SolutionsModule, cast(_DesignModuleProvider, design).GetModule("Solutions"))

    raw_excitation_names = list(getattr(hfss, "excitation_names", []))
    excitation_names = [str(name) for name in raw_excitation_names if isinstance(name, str) and str(name).strip()]
    tx_source_name = _find_excitation_name(
        preferred_names=list(ports.get("tx", [])),
        excitation_names=excitation_names,
        exact_fallback="TX_TML",
        regex_fallback=r"^txs_.*_T1$",
        role="tx",
    )
    rx_source_name = _find_excitation_name(
        preferred_names=list(ports.get("rx", [])),
        excitation_names=excitation_names,
        exact_fallback="RX_TML",
        regex_fallback=r"^rxs_.*_T1$",
        role="rx",
    )

    payload: list[object] = [
        [
            "UseIncidentVoltage:=",
            True,
            "IncludePortPostProcessing:=",
            False,
            "UseElementPatternMode:=",
            False,
            "SpecifySystemPower:=",
            False,
        ],
        [
            "Name:=",
            tx_source_name,
            "Magnitude:=",
            "1V",
            "Phase:=",
            "0deg",
        ],
        [
            "Name:=",
            rx_source_name,
            "Magnitude:=",
            "1V",
            "Phase:=",
            "90deg",
        ],
    ]
    solutions.EditSources(payload)
    return {
        "tx_source_name": tx_source_name,
        "tx_phase_deg": "0deg",
        "rx_source_name": rx_source_name,
        "rx_phase_deg": "90deg",
    }
