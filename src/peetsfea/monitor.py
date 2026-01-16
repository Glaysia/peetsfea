"""Minimal monitor UI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import config
from .types import AedtMachine, PyaedtProcessInfo


_D2CODING_URL = (
    "https://github.com/naver/d2codingfont/releases/download/VER1.3.2/"
    "D2Coding-Ver1.3.2-20180524.zip"
)
_D2CODING_TTF = "D2Coding-Ver1.3.2-20180524.ttf"
_FONT_DIR_NAME = "font"
_VIEWPORT_WIDTH = 980
_VIEWPORT_HEIGHT = 560

_MACHINE_COLUMNS = (
    "Machine",
    "IP",
    "AEDT",
    "Current",
    "Slurm",
    "Max AEDT",
)
_PROCESS_COLUMNS = (
    "IP",
    "Status",
    "GUI",
    "Stage",
    "Stage min",
    "Design",
    "TOML",
    "AEDT",
    "Machine info",
)


def _in_ipython() -> bool:
    try:
        from IPython import get_ipython  # type: ignore
    except Exception:
        return False
    return get_ipython() is not None


@dataclass(slots=True)
class MonitorHandle:
    """Return value for the monitor UI."""

    backend: str
    text: str
    root: Any | None = None


_ACTIVE_MONITOR: MonitorHandle | None = None


@dataclass(frozen=True, slots=True)
class MachineSnapshot:
    machine: AedtMachine
    processes: tuple[PyaedtProcessInfo, ...]


def _collect_machine_snapshots() -> list[MachineSnapshot]:
    snapshots: list[MachineSnapshot] = []
    for machine in config.machine_list:
        processes = config.pyaedt_processes_by_machine.get(machine.name, [])
        snapshots.append(MachineSnapshot(machine=machine, processes=tuple(processes)))
    return snapshots


def _format_bool(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "-"


def _format_minutes(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}m"


def _machine_info_text(machine: AedtMachine) -> str:
    current = "local" if machine.is_current_pc else "remote"
    slurm = "yes" if machine.use_slurm else "no"
    if machine.max_aedt_instances is None:
        max_instances = "-"
    else:
        max_instances = str(machine.max_aedt_instances)
    return f"{machine.name} | {current}, slurm={slurm}, max={max_instances}"


def _process_row_values(
    machine: AedtMachine,
    process: PyaedtProcessInfo,
) -> tuple[str, ...]:
    ip_address = process.ip_address or machine.ip_address or "-"
    status = process.status or "unknown"
    gui = _format_bool(process.gui_enabled)
    stage = process.stage or "unknown"
    stage_min = _format_minutes(process.stage_elapsed_min)
    design = process.design_name or "-"
    toml = process.toml_path or "-"
    aedt_version = process.aedt_version or machine.aedt_version or "-"
    machine_info = process.machine_info or _machine_info_text(machine)
    return (
        ip_address,
        status,
        gui,
        stage,
        stage_min,
        design,
        toml,
        aedt_version,
        machine_info,
    )


def _monitor_text(snapshot: list[MachineSnapshot]) -> str:
    total_processes = sum(len(item.processes) for item in snapshot)
    lines = [
        "peetsfea monitor",
        f"machines: {len(snapshot)}",
        f"processes: {total_processes}",
    ]
    if not snapshot:
        lines.append("note: no machines configured")
    return "\n".join(lines)


def _font_dir() -> "Path":
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / _FONT_DIR_NAME


def _ensure_font_file() -> str | None:
    from io import BytesIO
    from pathlib import Path
    from urllib.request import urlopen
    from zipfile import ZipFile

    font_dir = _font_dir()
    try:
        font_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return None

    ttf_files = sorted(font_dir.glob("*.ttf"))
    if ttf_files:
        for path in ttf_files:
            if path.name == _D2CODING_TTF:
                return str(path)
        return str(ttf_files[0])

    try:
        with urlopen(_D2CODING_URL, timeout=20) as resp:
            data = resp.read()
    except Exception:
        return None

    try:
        with ZipFile(BytesIO(data)) as zf:
            member = None
            for name in zf.namelist():
                if name.endswith(_D2CODING_TTF):
                    member = name
                    break
            if member is None:
                for name in zf.namelist():
                    if name.lower().endswith(".ttf"):
                        member = name
                        break
            if member is None:
                return None
            target = font_dir / Path(member).name
            target.write_bytes(zf.read(member))
            return str(target)
    except Exception:
        return None


def _machine_row_values(machine: AedtMachine) -> tuple[str, ...]:
    ip_address = machine.ip_address or "-"
    aedt_version = machine.aedt_version or "-"
    current = "yes" if machine.is_current_pc else "no"
    slurm = "yes" if machine.use_slurm else "no"
    if machine.max_aedt_instances is None:
        max_instances = "-"
    else:
        max_instances = str(machine.max_aedt_instances)
    return (ip_address, aedt_version, current, slurm, max_instances)


def _empty_process_row(machine: AedtMachine) -> tuple[str, ...]:
    ip_address = machine.ip_address or "-"
    aedt_version = machine.aedt_version or "-"
    return (
        ip_address,
        "no processes",
        "-",
        "-",
        "-",
        "-",
        "-",
        aedt_version,
        _machine_info_text(machine),
    )


def _render_process_table_dpg(
    dpg: Any,
    machine: AedtMachine,
    processes: tuple[PyaedtProcessInfo, ...],
) -> None:
    with dpg.table(
        header_row=True,
        policy=dpg.mvTable_SizingStretchProp,
        row_background=True,
        borders_innerH=True,
        borders_outerH=True,
        borders_innerV=True,
        borders_outerV=True,
    ):
        for label in _PROCESS_COLUMNS:
            dpg.add_table_column(label=label)
        if not processes:
            with dpg.table_row():
                for value in _empty_process_row(machine):
                    dpg.add_text(value)
            return
        for process in processes:
            with dpg.table_row():
                for value in _process_row_values(machine, process):
                    dpg.add_text(value)


def _render_machine_table_dpg(
    dpg: Any,
    snapshot: list[MachineSnapshot],
) -> None:
    with dpg.table(
        header_row=True,
        policy=dpg.mvTable_SizingStretchProp,
        row_background=True,
        borders_innerH=True,
        borders_outerH=True,
        borders_innerV=True,
        borders_outerV=True,
    ):
        for label in _MACHINE_COLUMNS:
            dpg.add_table_column(label=label)
        if not snapshot:
            with dpg.table_row():
                dpg.add_text("no machines configured")
                for _ in _MACHINE_COLUMNS[1:]:
                    dpg.add_text("-")
            return
        for item in snapshot:
            machine = item.machine
            with dpg.table_row():
                with dpg.tree_node(label=machine.name, default_open=False):
                    _render_process_table_dpg(dpg, machine, item.processes)
                for value in _machine_row_values(machine):
                    dpg.add_text(value)


def _build_inline_monitor_html(snapshot: list[MachineSnapshot]) -> str:
    from html import escape

    total_processes = sum(len(item.processes) for item in snapshot)
    rows: list[str] = []
    if not snapshot:
        rows.append("<div style='color: #666;'>no machines configured</div>")
    for item in snapshot:
        machine = item.machine
        machine_summary = " | ".join(
            [
                escape(machine.name),
                f"ip={escape(machine.ip_address or '-')}",
                f"aedt={escape(machine.aedt_version or '-')}",
                f"current={'yes' if machine.is_current_pc else 'no'}",
                f"slurm={'yes' if machine.use_slurm else 'no'}",
                f"max={escape(str(machine.max_aedt_instances)) if machine.max_aedt_instances is not None else '-'}",
            ]
        )
        rows.append(
            "<details style='margin-top: 10px;'>"
            f"<summary style='cursor: pointer; font-weight: 600;'>{machine_summary}</summary>"
        )
        rows.append("<div style='margin-top: 8px;'>")
        rows.append("<table style='width: 100%; border-collapse: collapse;'>")
        rows.append(
            "<thead><tr>"
            + "".join(
                "<th style='text-align: left; padding: 6px; border-bottom: 1px solid #ddd;'>"
                f"{escape(label)}"
                "</th>"
                for label in _PROCESS_COLUMNS
            )
            + "</tr></thead>"
        )
        rows.append("<tbody>")
        processes = item.processes or (None,)
        for process in processes:
            if process is None:
                values = _empty_process_row(machine)
            else:
                values = _process_row_values(machine, process)
            rows.append(
                "<tr>"
                + "".join(
                    "<td style='padding: 6px; border-bottom: 1px solid #f0f0f0;'>"
                    f"{escape(value)}"
                    "</td>"
                    for value in values
                )
                + "</tr>"
            )
        rows.append("</tbody></table>")
        rows.append("</div></details>")

    return (
        "<div style='font-family: ui-monospace, SFMono-Regular, Menlo, monospace;"
        " border: 1px solid #bbb; padding: 12px; border-radius: 8px;'>"
        "<div style='font-weight: 700; margin-bottom: 6px;'>peetsfea monitor</div>"
        f"<div>machines: {len(snapshot)}</div>"
        f"<div>processes: {total_processes}</div>"
        "<div style='margin-top: 10px; border-top: 1px solid #eee; padding-top: 8px;'>"
        + "".join(rows)
        + "</div>"
        "</div>"
    )


def _reuse_dpg_monitor() -> MonitorHandle | None:
    global _ACTIVE_MONITOR
    if _ACTIVE_MONITOR is None or _ACTIVE_MONITOR.backend != "dearpygui":
        return None
    return _ACTIVE_MONITOR


def _try_start_dpg_monitor(
    snapshot: list[MachineSnapshot],
    text: str,
) -> MonitorHandle | None:
    existing = _reuse_dpg_monitor()
    if existing is not None:
        return existing

    try:
        import dearpygui.dearpygui as dpg
    except Exception:
        return None

    dpg.create_context()

    font_path = _ensure_font_file()
    if font_path is not None:
        with dpg.font_registry():
            with dpg.font(font_path, 16) as font_id:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Korean)
        dpg.bind_font(font_id)

    total_processes = sum(len(item.processes) for item in snapshot)
    with dpg.window(
        label="peetsfea monitor",
        tag="peetsfea_monitor",
        width=_VIEWPORT_WIDTH,
        height=_VIEWPORT_HEIGHT,
    ):
        dpg.add_text("peetsfea monitor")
        dpg.add_text(f"machines: {len(snapshot)}")
        dpg.add_text(f"processes: {total_processes}")
        dpg.add_spacer(height=6)
        _render_machine_table_dpg(dpg, snapshot)

    dpg.set_primary_window("peetsfea_monitor", True)
    dpg.create_viewport(
        title="peetsfea monitor",
        width=_VIEWPORT_WIDTH,
        height=_VIEWPORT_HEIGHT,
        resizable=True,
    )
    dpg.setup_dearpygui()
    dpg.show_viewport()

    handle = MonitorHandle(backend="dearpygui", text=text, root=None)
    global _ACTIVE_MONITOR
    _ACTIVE_MONITOR = handle

    dpg.start_dearpygui()
    dpg.destroy_context()
    _ACTIVE_MONITOR = None
    return handle


def _start_inline_monitor(
    snapshot: list[MachineSnapshot],
    text: str,
) -> str:
    if _in_ipython():
        try:
            from IPython.display import HTML, display  # type: ignore

            html = _build_inline_monitor_html(snapshot)
            display(HTML(html))
            return html
        except Exception:
            pass
    print(text)
    return text


def start_monitor() -> MonitorHandle | str:
    """Start a minimal monitor UI, preferring a separate GUI window."""
    snapshot = _collect_machine_snapshots()
    text = _monitor_text(snapshot)
    handle = _try_start_dpg_monitor(snapshot, text)
    if handle is not None:
        return handle
    return _start_inline_monitor(snapshot, text)
