"""Minimal monitor UI helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_D2CODING_URL = (
    "https://github.com/naver/d2codingfont/releases/download/VER1.3.2/"
    "D2Coding-Ver1.3.2-20180524.zip"
)
_D2CODING_TTF = "D2Coding-Ver1.3.2-20180524.ttf"
_FONT_DIR_NAME = "font"
_VIEWPORT_WIDTH = 360
_VIEWPORT_HEIGHT = 220


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


def _reuse_dpg_monitor() -> MonitorHandle | None:
    global _ACTIVE_MONITOR
    if _ACTIVE_MONITOR is None or _ACTIVE_MONITOR.backend != "dearpygui":
        return None
    return _ACTIVE_MONITOR


def _try_start_dpg_monitor(text: str) -> MonitorHandle | None:
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

    with dpg.window(
        label="peetsfea monitor",
        tag="peetsfea_monitor",
        width=_VIEWPORT_WIDTH,
        height=_VIEWPORT_HEIGHT,
        no_resize=True,
    ):
        dpg.add_text("peetsfea monitor")
        dpg.add_text("status: idle")
        dpg.add_text("jobs: 0")
        dpg.add_text("한글 테스트: 정상 표시")
        dpg.add_text("note: this is a placeholder UI", color=(102, 102, 102))

    dpg.set_primary_window("peetsfea_monitor", True)
    dpg.create_viewport(
        title="peetsfea monitor",
        width=_VIEWPORT_WIDTH,
        height=_VIEWPORT_HEIGHT,
        resizable=False,
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


def _start_inline_monitor(text: str) -> str:
    if _in_ipython():
        try:
            from IPython.display import HTML, display  # type: ignore

            html = (
                "<div style='font-family: ui-monospace, SFMono-Regular, Menlo, monospace;"
                " border: 1px solid #bbb; padding: 12px; border-radius: 8px;'>"
                "<div style='font-weight: 700; margin-bottom: 6px;'>peetsfea monitor</div>"
                "<div>status: idle</div>"
                "<div>jobs: 0</div>"
                "<div style='color: #666; margin-top: 6px;'>note: this is a placeholder UI</div>"
                "</div>"
            )
            display(HTML(html))
            return html
        except Exception:
            pass
    print(text)
    return text


def start_monitor() -> MonitorHandle | str:
    """Start a minimal monitor UI, preferring a separate GUI window."""
    text = (
        "peetsfea monitor\n"
        "status: idle\n"
        "jobs: 0\n"
        "note: this is a placeholder UI"
    )
    handle = _try_start_dpg_monitor(text)
    if handle is not None:
        return handle
    return _start_inline_monitor(text)
