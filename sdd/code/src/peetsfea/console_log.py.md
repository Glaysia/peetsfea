---
title: console_log.py
created: 2026-06-10
updated: 2026-06-10
tags:
  - sdd
  - code
---

# console_log.py

- Path: `src/peetsfea/console_log.py`
- Responsibility: provide lightweight PeetsFEA console logging helpers and a call-duration decorator for local timing diagnostics.
- Inputs: message strings, JSON-serializable payloads, decorated callables, stdout/stderr TTY capabilities, and `NO_COLOR`/`TERM` environment values.
- Outputs: flushed stdout/stderr log lines with a PeetsFEA prefix; duration logs use a blue TTY line and include decorated stack depth, fully qualified function name, and elapsed milliseconds.
- Canonical state: ANSI color support decision per output stream and a context-local decorated-call depth counter.
- Invariants: log helpers do not buffer silently, color is disabled for `NO_COLOR` or dumb terminals, decorated call depth is restored after every call, and duration logs are emitted from `finally` so exceptions still produce timing output.
- Fail-fast points: decorated functions propagate their original exception after the timing log is emitted.
- Collaborators: none.
- Tests: [test_console_log.py](../../tests/test_console_log.py.md).
- Change hazards: keep this module dependency-light; do not route diagnostic timing through a fallback logging backend or swallow wrapped-function failures.
