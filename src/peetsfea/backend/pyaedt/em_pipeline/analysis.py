from __future__ import annotations

from peetsfea.types.manifest import EmPolicy


def build_analysis(policy: EmPolicy) -> dict[str, float | str]:
    return {
        "setup_frequency_hz": float(policy["setup_frequency_hz"]),
        "sweep_start_hz": float(policy["sweep_start_hz"]),
        "sweep_stop_hz": float(policy["sweep_stop_hz"]),
    }


def build_post_templates() -> list[str]:
    return ["s_parameters", "z_parameters"]
