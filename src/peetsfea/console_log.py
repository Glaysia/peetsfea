from __future__ import annotations

import json
import os
import sys
from typing import TextIO


_PEETSFEA_INFO_RGB = (46, 111, 172)
_ANSI_RESET = "\033[0m"


def _supports_color(stream: TextIO) -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM", "") == "dumb":
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def _colorize(text: str, *, rgb: tuple[int, int, int], stream: TextIO) -> str:
    if not _supports_color(stream):
        return text
    return f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m{text}{_ANSI_RESET}"


def _emit(level: str, message: str, *, stream: TextIO) -> None:
    prefix = _colorize(f"PeetsFEA {level}:", rgb=_PEETSFEA_INFO_RGB, stream=stream)
    stream.write(f"{prefix} {message}\n")
    stream.flush()


def info(message: str) -> None:
    _emit("INFO", message, stream=sys.stdout)


def warn(message: str) -> None:
    _emit("WARN", message, stream=sys.stdout)


def error(message: str) -> None:
    _emit("ERROR", message, stream=sys.stderr)


def info_json(payload: object) -> None:
    info(json.dumps(payload, ensure_ascii=False))
