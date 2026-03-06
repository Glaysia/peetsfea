from __future__ import annotations

import pytest
from typing import cast

from ansys.aedt.core import Hfss

from peetsfea.backend.pyaedt.em_pipeline.sources import apply_sources_phase


class _FakeHfssForSources:
    def __init__(self, excitation_names: list[str]) -> None:
        self.excitation_names = excitation_names
        self.edited_sources_payloads: list[list[object]] = []
        self.odesign = self._Design(self)

    class _Design:
        def __init__(self, parent: "_FakeHfssForSources") -> None:
            self._parent = parent

        class _SolutionsModule:
            def __init__(self, parent: "_FakeHfssForSources") -> None:
                self._parent = parent

            def EditSources(self, payload: list[object]) -> None:
                self._parent.edited_sources_payloads.append(payload)

        def GetModule(self, name: str) -> object:
            if name == "Solutions":
                return _FakeHfssForSources._Design._SolutionsModule(self._parent)
            raise ValueError(f"unexpected module: {name}")


def test_apply_sources_phase_uses_named_tx_rx_ports() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML", "RX_TML"])
    result = apply_sources_phase(cast(Hfss, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})

    assert result["tx_source_name"] == "TX_TML"
    assert result["rx_source_name"] == "RX_TML"
    assert result["tx_phase_deg"] == "0deg"
    assert result["rx_phase_deg"] == "90deg"
    assert fake_hfss.edited_sources_payloads
    payload = fake_hfss.edited_sources_payloads[0]
    payload_text = str(payload)
    assert "TX_TML" in payload_text
    assert "RX_TML" in payload_text
    assert "90deg" in payload_text


def test_apply_sources_phase_falls_back_to_short_rx_stub_excitation() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML", "rxs_rx_main_1_1_A_T1"])
    result = apply_sources_phase(cast(Hfss, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})

    assert result["rx_source_name"] == "rxs_rx_main_1_1_A_T1"
    assert fake_hfss.edited_sources_payloads
    assert "rxs_rx_main_1_1_A_T1" in str(fake_hfss.edited_sources_payloads[0])


def test_apply_sources_phase_raises_when_rx_source_is_missing() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML"])

    with pytest.raises(ValueError, match="Could not resolve rx source excitation name"):
        apply_sources_phase(cast(Hfss, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})
