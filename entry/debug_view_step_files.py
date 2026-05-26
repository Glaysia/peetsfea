VIEW_INDEX = 0
BUILD_W_GUI = True

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import build123d as bd
from build123d.topology import Shape
from ocp_vscode import Camera
from ocp_vscode import show
from ocp_vscode import show_clear

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peetsfea.backend.pyaedt import type2_step_import_style as aedt_style
from peetsfea.type2_sampled import DesignVariableEntry
from peetsfea.type2_sampled import PreparedType2Build
from peetsfea.type2_sampled import prepared_builds_from_manifest
from peetsfea.type2_step_export import export_type2_step_artifacts

REPO_ROOT = Path(__file__).resolve().parents[1]
TYPE2_FIXED_SOURCE_TOML_PATH = REPO_ROOT / "examples" / "type2_fixed.toml"
TYPE2_FIXED_OUTPUT_DIR = REPO_ROOT / "run" / "step" / "type2"
TYPE2_FIXED_LEDGER_PATH = TYPE2_FIXED_OUTPUT_DIR / "type2_step_ledger.json"
TYPE2_SAMPLED_MANIFEST_PATH = REPO_ROOT / "run" / "sampled" / "type2" / "manifest.json"
_REFRESHED_SAMPLED_STEP_PATHS_BY_SAMPLE_INDEX: dict[int, Path] = {}

ViewerStyle = tuple[tuple[int, int, int], float]


@dataclass(frozen=True)
class Type2GuiBuildInputs:
    design_name: str
    step_ledger_path: Path
    output_aedt_path: Path
    imported_ledger_path: Path
    design_variables: tuple[DesignVariableEntry, ...]


def selected_manifest_entry_for_sample_index(sample_index: int) -> dict[str, object]:
    if not isinstance(sample_index, int):
        raise TypeError(f"sample_index must be int (actual={type(sample_index).__name__})")
    if sample_index < 0:
        raise ValueError(f"sampled manifest selection requires sample_index >= 0 (actual={sample_index})")
    manifest = json.loads(TYPE2_SAMPLED_MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise TypeError("sample manifest root must be a table")
    entries = manifest["entries"]
    if not isinstance(entries, list):
        raise TypeError("manifest.entries must be a list")
    selected_entries = [entry for entry in entries if isinstance(entry, dict) and entry["sample_index"] == sample_index]
    if len(selected_entries) != 1:
        raise ValueError(f"manifest must contain exactly one entry for sample_index={sample_index}")
    return cast(dict[str, object], selected_entries[0])


def manifest_string(selected_entry: dict[str, object], key: str) -> str:
    raw_value = selected_entry[key]
    if not isinstance(raw_value, str) or raw_value == "":
        raise TypeError(f"manifest entry {key} must be a non-empty string")
    return raw_value


def manifest_path(selected_entry: dict[str, object], key: str) -> Path:
    return Path(manifest_string(selected_entry, key))


def manifest_int(selected_entry: dict[str, object], key: str) -> int:
    raw_value = selected_entry[key]
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise TypeError(f"manifest entry {key} must be int")
    return raw_value


def alpha_from_transparency(transparency: float) -> float:
    if transparency < 0.0 or transparency > 1.0:
        raise ValueError(f"viewer transparency must be in [0, 1] (actual={transparency})")
    return 1.0 - transparency


_NON_MODEL_STYLE: ViewerStyle = (
    aedt_style._NON_MODEL_COLOR,
    alpha_from_transparency(aedt_style._NON_MODEL_TRANSPARENCY),
)
_PCB_STYLE: ViewerStyle = (
    aedt_style._TX_PCB_COLOR,
    alpha_from_transparency(aedt_style._TX_PCB_TRANSPARENCY),
)
_COPPER_STYLE: ViewerStyle = (
    aedt_style._TX_COPPER_COLOR,
    alpha_from_transparency(aedt_style._TX_COPPER_TRANSPARENCY),
)
_FERRITE_STYLE: ViewerStyle = (
    aedt_style._TX_UNDERLAY_FERRITE_COLOR,
    alpha_from_transparency(aedt_style._TX_UNDERLAY_FERRITE_TRANSPARENCY),
)
_PET_PSA_STYLE: ViewerStyle = (
    aedt_style._TX_UNDERLAY_PET_PSA_COLOR,
    alpha_from_transparency(aedt_style._TX_UNDERLAY_PET_PSA_TRANSPARENCY),
)
_AIR_STYLE: ViewerStyle = (
    aedt_style._TX_UNDERLAY_AIR_COLOR,
    alpha_from_transparency(aedt_style._TX_UNDERLAY_AIR_TRANSPARENCY),
)


def viewer_style_from_label(label: str) -> ViewerStyle:
    if label.startswith(
        (
            "tx_copper",
            "tx_inner_copper",
            "tx_outer_copper",
            "rx_copper",
            "tx_tube",
            "tx_inner_tube",
            "rx_tube",
            "tx_bridge",
            "rx_bridge",
            "tx_stub",
            "rx_stub",
        )
    ):
        return _COPPER_STYLE
    if label.startswith(("tx_pcb", "tx_inner_pcb", "tx_outer_pcb", "rx_pcb")):
        return _PCB_STYLE
    if label.startswith(aedt_style._UNDERLAY_FERRITE_NAME_PREFIXES):
        return _FERRITE_STYLE
    if label.startswith(aedt_style._UNDERLAY_PET_PSA_NAME_PREFIXES):
        return _PET_PSA_STYLE
    if label.startswith(aedt_style._UNDERLAY_AIR_NAME_PREFIXES):
        return _AIR_STYLE
    return _NON_MODEL_STYLE


def child_shapes(shape: Shape) -> list[Shape]:
    children = tuple(shape.children)
    if children:
        return [cast(Shape, child) for child in children]
    return [shape]


def viewer_payload_for_shape(
    shape: Shape,
    *,
    fallback_name: str,
) -> tuple[list[Shape], list[str], list[tuple[int, int, int]], list[float]]:
    entries = child_shapes(shape)
    cad_objs: list[Shape] = []
    names: list[str] = []
    colors: list[tuple[int, int, int]] = []
    alphas: list[float] = []
    for index, entry in enumerate(entries):
        entry_label = entry.label if isinstance(entry.label, str) and entry.label != "" else f"{fallback_name}_{index}"
        color, alpha = viewer_style_from_label(entry_label)
        cad_objs.append(entry)
        names.append(entry_label)
        colors.append(color)
        alphas.append(alpha)
    return (cad_objs, names, colors, alphas)


def fixed_scene_step_path() -> Path:
    fixed_ledger = export_type2_step_artifacts(
        toml_path=TYPE2_FIXED_SOURCE_TOML_PATH,
        output_dir=TYPE2_FIXED_OUTPUT_DIR,
        ledger_path=TYPE2_FIXED_LEDGER_PATH,
        seed=0,
    )
    scene_step_path = Path(cast(str, fixed_ledger["scene_step_path"]))
    print("mode: fixed example")
    print(f"source TOML: {TYPE2_FIXED_SOURCE_TOML_PATH}")
    print(f"scene STEP: {scene_step_path}")
    print(f"ledger JSON: {TYPE2_FIXED_LEDGER_PATH}")
    return scene_step_path


def sampled_scene_step_path(view_index: int) -> Path:
    selected_entry = selected_manifest_entry_for_sample_index(sample_index=view_index)
    step_ledger_path = manifest_path(selected_entry, "step_ledger_path")
    scene_step_path = refresh_sampled_step_path(selected_entry)
    print("mode: sampled manifest")
    print(f"manifest: {TYPE2_SAMPLED_MANIFEST_PATH}")
    print(f"sample index: {selected_entry['sample_index']}")
    print(f"design_id: {selected_entry['design_id']}")
    print(f"seed: {selected_entry['seed']}")
    print(f"retry: {selected_entry['retry_number']}")
    print(f"scene STEP: {scene_step_path}")
    print(f"ledger JSON: {step_ledger_path}")
    return scene_step_path


def refresh_sampled_step_path(selected_entry: dict[str, object]) -> Path:
    sample_index = manifest_int(selected_entry, "sample_index")
    if sample_index in _REFRESHED_SAMPLED_STEP_PATHS_BY_SAMPLE_INDEX:
        return _REFRESHED_SAMPLED_STEP_PATHS_BY_SAMPLE_INDEX[sample_index]
    manifest_scene_step_path = manifest_path(selected_entry, "scene_step_path")
    step_ledger_path = manifest_path(selected_entry, "step_ledger_path")
    generated_ledger = export_type2_step_artifacts(
        toml_path=manifest_path(selected_entry, "sampled_toml_path"),
        output_dir=manifest_path(selected_entry, "design_dir"),
        ledger_path=step_ledger_path,
        seed=manifest_int(selected_entry, "seed"),
    )
    scene_step_path = Path(cast(str, generated_ledger["scene_step_path"]))
    if scene_step_path != manifest_scene_step_path:
        raise ValueError(
            "generated sampled STEP path must match manifest path "
            f"(sample_index={sample_index}, generated={scene_step_path}, manifest={manifest_scene_step_path})"
        )
    if not step_ledger_path.is_file():
        raise FileNotFoundError(f"generated sampled STEP ledger is missing: {step_ledger_path}")
    print(f"refreshed sampled STEP: {scene_step_path}")
    _REFRESHED_SAMPLED_STEP_PATHS_BY_SAMPLE_INDEX[sample_index] = scene_step_path
    return scene_step_path


def scene_step_path_for_view_index(view_index: int) -> Path:
    if view_index == -1:
        return fixed_scene_step_path()
    return sampled_scene_step_path(view_index)


def show_scene_step(scene_step_path: Path) -> None:
    shown_step = cast(Shape, bd.import_step(scene_step_path))
    cad_objs, names, colors, alphas = viewer_payload_for_shape(shown_step, fallback_name="type2_scene")
    show(
        *cad_objs,
        names=names,
        colors=colors,
        alphas=alphas,
        transparent=True,
        reset_camera=Camera.RESET,
    )


def prepared_build_for_design_id(design_id: str) -> PreparedType2Build:
    prepared_builds = prepared_builds_from_manifest(
        TYPE2_SAMPLED_MANIFEST_PATH,
        selected_design_ids=(design_id,),
    )
    if len(prepared_builds) != 1:
        raise RuntimeError(f"manifest must resolve exactly one prepared build for design_id={design_id}")
    return prepared_builds[0]


def fixed_gui_build_inputs() -> Type2GuiBuildInputs:
    fixed_scene_step_path()
    return Type2GuiBuildInputs(
        design_name="type2_fixed",
        step_ledger_path=TYPE2_FIXED_LEDGER_PATH,
        output_aedt_path=TYPE2_FIXED_OUTPUT_DIR / "type2_fixed.aedt",
        imported_ledger_path=TYPE2_FIXED_OUTPUT_DIR / "type2_imported_ledger.json",
        design_variables=(),
    )


def sampled_gui_build_inputs(view_index: int) -> Type2GuiBuildInputs:
    selected_entry = selected_manifest_entry_for_sample_index(sample_index=view_index)
    design_id = manifest_string(selected_entry, "design_id")
    step_ledger_path = manifest_path(selected_entry, "step_ledger_path")
    output_aedt_path = manifest_path(selected_entry, "aedt_path")
    imported_ledger_path = manifest_path(selected_entry, "imported_ledger_path")
    prepared_build = prepared_build_for_design_id(design_id)
    if prepared_build.step_ledger_path != step_ledger_path:
        raise ValueError(f"prepared step ledger path mismatch for design_id={design_id}")
    if prepared_build.aedt_path != output_aedt_path:
        raise ValueError(f"prepared AEDT path mismatch for design_id={design_id}")
    if prepared_build.imported_ledger_path != imported_ledger_path:
        raise ValueError(f"prepared imported ledger path mismatch for design_id={design_id}")
    scene_step_path = refresh_sampled_step_path(selected_entry)
    print(f"manifest: {TYPE2_SAMPLED_MANIFEST_PATH}")
    print(f"debug design_id: {design_id}")
    print(f"sampled STEP: {scene_step_path}")
    print(f"sampled STEP ledger: {step_ledger_path}")
    return Type2GuiBuildInputs(
        design_name=design_id,
        step_ledger_path=step_ledger_path,
        output_aedt_path=output_aedt_path,
        imported_ledger_path=imported_ledger_path,
        design_variables=tuple(prepared_build.design_variables),
    )


def gui_build_inputs_for_view_index(view_index: int) -> Type2GuiBuildInputs:
    if view_index == -1:
        return fixed_gui_build_inputs()
    return sampled_gui_build_inputs(view_index)


def build_with_gui(view_index: int) -> None:
    from peetsfea.aedt import Hfss
    from peetsfea.aedt.protocols import HfssSession
    from peetsfea.backend.pyaedt.type2_step_setup_ready import setup_type2_step_ledger_into_hfss

    build_inputs = gui_build_inputs_for_view_index(view_index)
    hfss = cast(
        HfssSession,
        Hfss(
            design=build_inputs.design_name,
            non_graphical=False,
            new_desktop=False,
            close_on_exit=False,
        ),
    )
    result = setup_type2_step_ledger_into_hfss(
        hfss=hfss,
        step_ledger_path=build_inputs.step_ledger_path,
        output_aedt_path=build_inputs.output_aedt_path,
        imported_ledger_path=build_inputs.imported_ledger_path,
        design_variables=build_inputs.design_variables,
        run_aedt_design_validation=True,
    )
    print(f"AEDT: {result['aedt_path']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--view-index", type=int, default=VIEW_INDEX)
    parser.add_argument(
        "--build-w-gui",
        action=argparse.BooleanOptionalAction,
        default=BUILD_W_GUI,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    view_index = cast(int, args.view_index)
    build_w_gui = cast(bool, args.build_w_gui)
    print(f"repo root: {REPO_ROOT}")
    print(f"view index: {view_index}")
    print(f"BUILD_W_GUI: {build_w_gui}")
    show_clear()
    print("viewer cleared")
    scene_step_path = scene_step_path_for_view_index(view_index)
    show_scene_step(scene_step_path)
    if build_w_gui:
        build_with_gui(view_index)
    else:
        print("BUILD_W_GUI is False; GUI build skipped")


if __name__ == "__main__":
    main()
