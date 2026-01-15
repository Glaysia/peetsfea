# AGENTS

This document defines the project rules for coding agents working in this repository.

## Project goals
- **Spec-first design**: The TOML spec is the single source of truth (SSOT).
- **Determinism**: Same spec + same version + same seed => same results.
- **Pyaedt backend**: Delegate modeling/simulation to Pyaedt.
- **Dataset generation**: Produce datasets via parameter sweeps/sampling.

## Working principles
- Any spec change must be reflected in docs (README or spec docs).
- Random/sampling logic must always accept an explicit `seed`.
- Document defaults; do not hide implicit values.
- Keep Pyaedt-dependent code isolated and replaceable.
- Do not add features that assume a UI/GUI.

## Spec rules
- Use standard TOML only (no custom DSL).
- Consider a spec version bump when adding new parameters.
- Keep spec `path` as a stable dot notation.

## Tests/execution
- Prefer pure-Python tests for the spec parser/validator.
- Separate integration tests that require Pyaedt.
- Do not include large dataset generation in default test runs.

## File layout (planned)
- `peetsfea/`: library code
- `peetsfea/spec/`: schema/validation/normalization
- `peetsfea/backend/`: Pyaedt adapters
- `examples/`: TOML examples
- `docs/`: spec/design docs

