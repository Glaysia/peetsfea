from __future__ import annotations

import pytest
from typing import cast

from peetsfea.aedt import Hfss

from peetsfea.backend.pyaedt.em_pipeline.steps.sources import apply_sources_phase


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
    assert result["tx_magnitude"] == "288V"
    assert result["rx_magnitude"] == "0V"
    assert result["tx_phase_deg"] == "0deg"
    assert result["rx_phase_deg"] == "0deg"
    assert fake_hfss.edited_sources_payloads
    payload = fake_hfss.edited_sources_payloads[0]
    payload_text = str(payload)
    assert "TX_TML" in payload_text
    assert "RX_TML" in payload_text
    assert "288V" in payload_text
    assert "0V" in payload_text


def test_apply_sources_phase_prefers_geometry_captured_terminal_names() -> None:
    fake_hfss = _FakeHfssForSources(["1_T1", "2_T1"])
    result = apply_sources_phase(cast(Hfss, fake_hfss), {"tx": ["1_T1"], "rx": ["2_T1"]})

    assert result["tx_source_name"] == "1_T1"
    assert result["rx_source_name"] == "2_T1"
    payload_text = str(fake_hfss.edited_sources_payloads[0])
    assert "1_T1" in payload_text
    assert "2_T1" in payload_text
    assert "288V" in payload_text
    assert "0V" in payload_text


def test_apply_sources_phase_accepts_parenthesized_geometry_captured_terminal_names() -> None:
    fake_hfss = _FakeHfssForSources(["(1_T1)", "(2_T1)"])
    result = apply_sources_phase(cast(Hfss, fake_hfss), {"tx": ["1_T1"], "rx": ["2_T1"]})

    assert result["tx_source_name"] == "(1_T1)"
    assert result["rx_source_name"] == "(2_T1)"
    payload_text = str(fake_hfss.edited_sources_payloads[0])
    assert "(1_T1)" in payload_text
    assert "(2_T1)" in payload_text
    assert "288V" in payload_text
    assert "0V" in payload_text


def test_apply_sources_phase_raises_when_rx_source_name_is_missing_even_if_stub_like_name_exists() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML", "rxs_rx_main_1_1_c_T1"])

    with pytest.raises(ValueError, match="rx source name is not available in HFSS excitation names"):
        apply_sources_phase(cast(Hfss, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})


def test_apply_sources_phase_raises_when_multiple_stub_like_names_exist_but_rx_source_name_is_missing() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML", "rxs_rx_main_0_0_A_T1", "rxs_rx_main_1_1_c_T1"])

    with pytest.raises(ValueError, match="rx source name is not available in HFSS excitation names"):
        apply_sources_phase(cast(Hfss, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})


def test_apply_sources_phase_raises_when_rx_source_is_missing() -> None:
    fake_hfss = _FakeHfssForSources(["TX_TML"])

    with pytest.raises(ValueError, match="rx source name is not available in HFSS excitation names"):
        apply_sources_phase(cast(Hfss, fake_hfss), {"tx": ["TX_TML"], "rx": ["RX_TML"]})
