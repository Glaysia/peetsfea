---
title: test_console_log.py
created: 2026-06-10
updated: 2026-06-10
tags:
  - sdd
  - code
  - test
---

# test_console_log.py

- Path: `tests/test_console_log.py`
- Responsibility: verify the console call-duration decorator emits usable timing diagnostics.
- Inputs: locally defined decorated functions and pytest `capsys`.
- Outputs: assertions for PeetsFEA INFO log lines, stack depth values, fully qualified function names, elapsed millisecond fields, and exception-path logging.
- Canonical state: captured stdout lines from nested decorated calls and a decorated function that raises.
- Invariants: nested calls report inner depth `2` before outer depth `1`, successful calls preserve return values, and raised calls still emit a timing line before propagating the exception.
- Fail-fast points: missing stack depth, function name, elapsed field, or exception propagation fails the test.
- Collaborators: [console_log.py](../src/peetsfea/console_log.py.md).
