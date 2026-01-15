"""Minimal monitor UI helpers."""

from __future__ import annotations

from typing import Any


def _in_ipython() -> bool:
    try:
        from IPython import get_ipython  # type: ignore
    except Exception:
        return False
    return get_ipython() is not None


def start_monitor() -> Any:
    """Start a minimal monitor UI placeholder for quick checks."""
    text = (
        "peetsfea monitor\n"
        "status: idle\n"
        "jobs: 0\n"
        "note: this is a placeholder UI"
    )
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
