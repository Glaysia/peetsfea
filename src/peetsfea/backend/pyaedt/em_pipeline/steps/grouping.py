from __future__ import annotations

from peetsfea.backend.pyaedt.em_pipeline.contracts import EmPipelineInput


def build_groups(em_input: EmPipelineInput) -> dict[str, list[str]]:
    ready = em_input["ready_objects"]
    return {
        "tx": sorted(ready["tx_conductors"]),
        "rx": sorted(ready["rx_conductors"]),
        "fr4": sorted(ready["fr4_objects"]),
    }
