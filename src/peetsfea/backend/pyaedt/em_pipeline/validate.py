from __future__ import annotations

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineResult
from peetsfea.types.manifest import EmPolicy


def validate_pipeline(result: EmPipelineResult, policy: EmPolicy) -> dict[str, str | bool]:
    groups = result["groups"]
    if "tx" not in groups:
        raise ValueError("EM pipeline validation requires groups['tx']")
    if "rx" not in groups:
        raise ValueError("EM pipeline validation requires groups['rx']")
    tx_ports = result["ports"]["tx"]
    rx_ports = result["ports"]["rx"]
    has_tx_group = len(groups["tx"]) > 0
    has_rx_group = len(groups["rx"]) > 0
    has_tx_port = len(tx_ports) == 1
    has_rx_port = len(rx_ports) == 1
    is_tx_rx_pair = has_tx_port and has_rx_port
    is_rx_only = (not has_tx_port) and has_rx_port and len(tx_ports) == 0
    if is_tx_rx_pair:
        ok = has_tx_group and has_rx_group
    elif is_rx_only:
        ok = has_rx_group
    else:
        ok = False
    gate = str(policy["validation_gate"])
    if gate == "hard_fail" and not ok:
        raise ValueError(
            "EM pipeline validation failed: invalid port mode or missing required conductor groups "
            f"(ports_tx={tx_ports}, ports_rx={rx_ports}, has_tx_group={has_tx_group}, has_rx_group={has_rx_group})"
        )
    return {
        "ok": ok,
        "gate": gate,
        "message": "ok" if ok else "invalid tx/rx mode or missing required conductors",
    }
