from __future__ import annotations

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineResult
from peetsfea.types.manifest import EmPolicy


def validate_pipeline(result: EmPipelineResult, policy: EmPolicy) -> dict[str, str | bool]:
    has_tx = len(result["groups"].get("tx", [])) > 0
    has_rx = len(result["groups"].get("rx", [])) > 0
    ok = has_tx and has_rx
    gate = str(policy["validation_gate"])
    if gate == "hard_fail" and not ok:
        raise ValueError("EM pipeline validation failed: tx/rx conductor groups are required")
    return {
        "ok": ok,
        "gate": gate,
        "message": "ok" if ok else "missing tx or rx conductors",
    }
