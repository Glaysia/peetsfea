from __future__ import annotations

from typing import cast

from peetsfea.aedt.protocols import DesignSession, HfssSession, SolutionsModuleSession
from peetsfea.backend.pyaedt.failfast import raise_on_false

from peetsfea.types.manifest import EmPorts

from .excitation_names import normalize_excitation_name, normalized_excitation_name_map


def _require_excitation_name(*, name: str, excitation_names: list[str], role: str) -> str:
    normalized_map = normalized_excitation_name_map(excitation_names)
    normalized_name = normalize_excitation_name(name)
    if normalized_name not in normalized_map:
        raise ValueError(
            f"{role} source name is not available in HFSS excitation names "
            f"(source={name}, available={sorted(normalized_map)})"
        )
    return normalized_map[normalized_name]


def apply_sources_phase(hfss: HfssSession, ports: EmPorts) -> dict[str, str]:
    design = cast(DesignSession, hfss.odesign)
    solutions = cast(SolutionsModuleSession, design.GetModule("Solutions"))
    excitation_names = list(hfss.excitation_names)
    tx_ports = list(ports["tx"])
    rx_ports = list(ports["rx"])
    is_tx_rx_pair = len(tx_ports) == 1 and len(rx_ports) == 1
    is_rx_only = len(tx_ports) == 0 and len(rx_ports) == 1
    if not (is_tx_rx_pair or is_rx_only):
        raise ValueError(
            "apply_sources_phase requires either one TX+one RX port pair or one RX-only port "
            f"(tx_ports={tx_ports}, rx_ports={rx_ports})"
        )
    if is_tx_rx_pair:
        tx_source_name = _require_excitation_name(
            name=tx_ports[0],
            excitation_names=excitation_names,
            role="tx",
        )
        rx_source_name = _require_excitation_name(
            name=rx_ports[0],
            excitation_names=excitation_names,
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
                "288V",
                "Phase:=",
                "0deg",
            ],
            [
                "Name:=",
                rx_source_name,
                "Magnitude:=",
                "0V",
                "Phase:=",
                "0deg",
            ],
        ]
        raise_on_false(
            solutions.EditSources(payload),
            operation="EditSources",
            context={"tx_source_name": tx_source_name, "rx_source_name": rx_source_name},
        )
        return {
            "tx_source_name": tx_source_name,
            "tx_phase_deg": "0deg",
            "tx_magnitude": "288V",
            "rx_source_name": rx_source_name,
            "rx_phase_deg": "0deg",
            "rx_magnitude": "0V",
        }

    rx_source_name = _require_excitation_name(
        name=rx_ports[0],
        excitation_names=excitation_names,
        role="rx",
    )
    payload = [
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
            rx_source_name,
            "Magnitude:=",
            "1V",
            "Phase:=",
            "0deg",
        ],
    ]
    raise_on_false(
        solutions.EditSources(payload),
        operation="EditSources",
        context={"rx_source_name": rx_source_name},
    )
    return {
        "rx_source_name": rx_source_name,
        "rx_phase_deg": "0deg",
        "rx_magnitude": "1V",
    }
