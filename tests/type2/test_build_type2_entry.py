from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pytest

import entry.build as build_entry
import peetsfea.type2_sampled as type2_sampled
from entry.build import build_type2
from entry.sample import sample_type2
from peetsfea.backend.pyaedt.type2_step_setup_ready import Type2SetupReadyResult
from peetsfea.type2_sampled import PreparedType2Build


@dataclass(frozen=True)
class _FakePlateStackModeledSpec:
    object_id: str
    role: str


@dataclass(frozen=True)
class _FakePlateStackType2Spec:
    modeled_objects: tuple[_FakePlateStackModeledSpec, ...]


def _patch_plate_stack_spec_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_spec = _FakePlateStackType2Spec(
        modeled_objects=(
            _FakePlateStackModeledSpec(object_id="tx_plate_stack", role="tx_plate_stack"),
            _FakePlateStackModeledSpec(object_id="rx_plate_stack", role="rx_plate_stack"),
        )
    )
    monkeypatch.setattr(type2_sampled, "load_type2_step_spec", lambda _path: fake_spec)


def _source_type2_toml_text() -> str:
    return """
spec_version = "0.2.22"
schema_id = "peetsfea.type2.step.v1"
runtime_compatible = false

[design]
units = "mm"

[backend]
authoring_tool = "build123d"
solver_tool = "hfss"
interchange_format = "step"

[simulation]
radiation_margin_mm = 3500.0

[outputs]
report_name = "Output Variables Table1"
solution_name = "Setup1 : LastAdaptive"
primary_sweep = "Freq"
report_category = "Terminal Solution Data"
plot_type = "Data Table"

[[outputs.variables]]
name = "Ltx_uH"
expression = "im(Zt(TX_TML,TX_TML))/2/pi/freq*1e6"

[[non_model_objects]]
id = "floor"
kind = "floor"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -10.0, -1.0]
size_xyz = [20.0, 20.0, 1.0]

[[non_model_objects]]
id = "shelf"
kind = "shelf"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "XY"
origin_xyz = [0.0, -10.0, 0.0]
size_xyz = [10.0, 20.0, 4.0]

[[non_model_objects]]
id = "wall"
kind = "wall"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [-1.0, -10.0, 0.0]
size_xyz = [1.0, 20.0, 10.0]

[[non_model_objects]]
id = "tv"
kind = "tv"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [0.0, -5.0, 5.0]
size_xyz = [1.0, 10.0, 4.0]

[[non_model_objects]]
id = "tx_region"
kind = "tx_region"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [0.0, -140.0, 0.0]
size_xyz = [160.0, 280.0, 90.0]

[[non_model_objects]]
id = "rx_region_max"
kind = "rx_region_max"
primitive = "box"
present = true
non_model = true
material = "vacuum"
plane = "YZ"
origin_xyz = [200.0, -100.0, 0.0]
size_xyz = [10.0, 200.0, 200.0]

[[modeled_objects]]
object_id = "tx_plate_stack"
role = "tx_plate_stack"
material = "composite"
model_state = true
pcb_total_thickness_mm = 1.6
copper_thickness_mm = 0.035
ferrite_set_count = 10

[[modeled_objects]]
object_id = "rx_plate_stack"
role = "rx_plate_stack"
material = "composite"
model_state = true
pcb_total_thickness_mm = 0.4
copper_thickness_mm = 0.1
ferrite_set_count = 10
""".strip()


def _write_source_type2_toml(tmp_path: Path) -> Path:
    path = tmp_path / "type2_sweep.toml"
    path.write_text(_source_type2_toml_text(), encoding="utf-8")
    return path


def test_build_type2_reads_aedt_builder_n_from_manifest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_plate_stack_spec_loader(monkeypatch)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=4,
        seed_n=2,
        sampler_n=1,
        aedt_builder_n=6,
        make_step_on_sample=False,
    )

    calls: list[dict[str, object]] = []

    def _fake_build_prepared_type2_designs(
        prepared_builds: tuple[PreparedType2Build, ...],
        *,
        jobs: int,
        exporter: object,
        runner: object,
    ) -> list[dict[str, str]]:
        calls.append(
            {
                "jobs": jobs,
                "build_count": len(prepared_builds),
                "modeled_roles": [tuple(prepared_build.modeled_roles) for prepared_build in prepared_builds],
                "design_variables": [tuple(prepared_build.design_variables) for prepared_build in prepared_builds],
                "exporter": exporter,
                "runner": runner,
            }
        )
        return []

    monkeypatch.setattr(build_entry, "build_prepared_type2_designs", _fake_build_prepared_type2_designs)
    results = build_type2(manifest_path=manifest_path)

    assert results == []
    assert calls == [
        {
            "jobs": 6,
            "build_count": 2,
            "modeled_roles": [("tx_plate_stack", "rx_plate_stack"), ("tx_plate_stack", "rx_plate_stack")],
            "design_variables": [(), ()],
            "exporter": build_entry.export_type2_step_artifacts,
            "runner": build_entry.setup_type2_step_ledger,
        }
    ]


def test_build_type2_rejects_plate_stack_manifest_before_export_or_runner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _patch_plate_stack_spec_loader(monkeypatch)
    source_toml_path = _write_source_type2_toml(tmp_path)
    output_dir = tmp_path / "run" / "sampled" / "type2"
    manifest_path = output_dir / "manifest.json"

    sample_type2(
        source_toml_path=source_toml_path,
        output_dir=output_dir,
        manifest_path=manifest_path,
        seed_first=8,
        seed_n=1,
        sampler_n=1,
        aedt_builder_n=2,
        make_step_on_sample=False,
    )
    exporter_calls: list[dict[str, object]] = []
    runner_calls: list[dict[str, object]] = []

    def _build_exporter(**kwargs: object) -> object:
        exporter_calls.append(dict(kwargs))
        raise AssertionError("build exporter must not be called for setup-ready-unsupported plate-stack manifests")

    def _runner(**kwargs: object) -> Type2SetupReadyResult:
        runner_calls.append(dict(kwargs))
        raise AssertionError("runner must not be called for setup-ready-unsupported plate-stack manifests")

    with pytest.raises(
        ValueError,
        match=r"type2 build/setup-ready is unsupported for modeled roles \['tx_plate_stack', 'rx_plate_stack'\]",
    ):
        build_type2(manifest_path=manifest_path, exporter=_build_exporter, runner=_runner)
    assert exporter_calls == []
    assert runner_calls == []


def test_build_type2_rejects_list_manifest_payload(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("[]", encoding="utf-8")

    with pytest.raises(TypeError, match=r"type2 sample manifest must be an object"):
        build_type2(manifest_path=manifest_path)


def test_build_type2_rejects_missing_aedt_builder_n_config(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "config": {
                    "source_toml_path": "/tmp/source.toml",
                    "seed_first": 0,
                    "seed_n": 1,
                    "sampler_n": 1,
                    "make_step_on_sample": True,
                },
                "entries": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"type2 sample manifest config is missing required key 'aedt_builder_n'"):
        build_type2(manifest_path=manifest_path)


def test_build_type2_rejects_missing_make_step_on_sample_config(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "config": {
                    "source_toml_path": "/tmp/source.toml",
                    "seed_first": 0,
                    "seed_n": 1,
                    "sampler_n": 1,
                    "aedt_builder_n": 1,
                },
                "entries": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"type2 sample manifest config is missing required key 'make_step_on_sample'"):
        build_type2(manifest_path=manifest_path)
