# DevPlan

This plan captures the development direction for distributed execution of spec-defined transformer/inductor/coil/WPT designs using Pyaedt (Ansys EDT) across local machines, SSH targets, and SSH+Slurm sessions.

## Goals
- Let a user author a detailed TOML spec (geometry + parameter ranges) with help from an LLM.
- Import this library in Python and dispatch jobs across a list of PCs.
- Support execution via:
  - local machine
  - SSH to a remote PC
  - SSH to a remote PC, then submit/attach to a Slurm job where AEDT runs
- Keep spec-first, deterministic behavior, and SSOT mapping intact.
- Provide robust timeouts and job monitoring for unstable AEDT runs.
- Support high concurrency (500+ parallel jobs) with consolidated status views.

## Assumptions
- AEDT (Ansys Electronics Desktop) is installed and licensed on target machines.
- Pyaedt is the only supported backend for modeling/simulation.
- AEDT is expected to run headless (GUI off);

## Architecture Overview
- Spec layer: TOML schema, validation, normalization, and deterministic parameter expansion.
- Config layer: runtime config objects set in Python (machines, process limits, and monitor snapshots).
- Execution layer: job planning and remote execution adapters.
- Backend layer: Pyaedt adapters that are isolated and replaceable.
- Result layer: structured outputs (logs, parameter manifests, result artifacts).
- Monitoring layer: job heartbeats, timeouts, and aggregated status reporting.

## Current Implementation Notes
- Monitor UI renders an expandable machine table with per-process columns.
- Runtime config stores machine lists and per-machine Pyaedt process snapshots.
- Process snapshots capture status, GUI mode, stage, stage duration, design, TOML, AEDT version, and machine info.

## Workstreams and Milestones

### 1) Spec + Validation (SSOT)
- Define stable spec paths for geometry, simulation, and dataset.
- Add explicit defaults in docs and spec docs; avoid implicit values.
- Implement deterministic parameter resolution (TOML + seed => concrete parameters).
- Preflight validation must report supported vs unsupported features.
- Keep TOML focused on design definitions; execution settings are managed in Python code.
- Compute a deterministic TOML hash and map it to a friendly unique identifier using
  adjective + scholar list + hash prefix (first two chars) as a suffix
  (200 adjectives, 300 scholars).

Deliverables:
- TOML spec docs and validator
- Determinism test suite
- TOML loader for design metadata plus deterministic hash + friendly-id mapping

### 2) Execution Model (Local/SSH/Slurm)
- Define Python-side execution target config schema (not in TOML):
  - local: python executable, AEDT path, environment overrides
  - ssh: host/user/key, ssh key path, remote working dir, AEDT path
  - ssh+slurm: host/user/key + slurm parameters (partition, time, nodes, constraints, modules)
- Extend machine config with:
  - ip address, ssh key path
  - slurm usage flag
  - slurm strategy (srun default; module loading policy)
  - max processes to schedule per machine
- Design a job manifest:
  - parameters, seed, spec version, backend version, target info
  - TOML hash, TOML path, and deterministic run id for traceability
- Build an execution planner that maps N parameter sets to M targets.
- Implement adapters:
  - LocalRunner
  - SshRunner (non-interactive, Fabric-based)
  - SshSlurmRunner (submit, monitor, fetch results, Fabric-based)

Deliverables:
- Execution target config section
- Job planner + runners
- Remote file staging (spec, manifest, script)
- Fabric-based SSH/Slurm execution adapter
- Python execution config schema and API

### 3) Monitoring + Timeout Control
- Define per-stage timeouts:
  - startup (AEDT launch)
  - model build
  - solve/run
  - result export
- Implement heartbeats emitted by each job to a central monitor.
- Aggregate per-job status:
  - state (queued/running/failed/timeout/completed)
  - TOML hash/name
  - seed
  - target
  - timestamps (start, last heartbeat, end)
- Provide a monitor data grid with expandable machine rows and per-process columns
  (IP, status, GUI, stage, stage minutes, design, TOML, AEDT version, machine info).
- Provide a scalable monitoring backend that can track 500+ active jobs.
- Expose monitor CLI/reporting (summary table and filter by status/target).

Deliverables:
- Monitoring spec section
- Heartbeat + timeout implementation
- Aggregated status view (CLI or report file)
- Monitor UI table with expandable machine rows and Pyaedt process details

### 4) Backend Integration (Pyaedt)
- Isolate AEDT interaction in backend modules.
- Provide a minimal, deterministic run entrypoint that accepts:
  - spec path
  - seed
  - output directory
- Ensure all random/sampling accepts a seed and is serialized in manifest.

Deliverables:
- Backend adapter interface
- Pyaedt run entrypoint

### 5) Dataset Generation
- Provide sampling and sweep strategies with deterministic outputs.
- Make dataset generation target-aware (distribute samples across targets).

Deliverables:
- Dataset generator
- Deterministic tests for sampling

### 6) Documentation
- Update README/spec docs for any spec additions.
- Provide execution examples:
  - local
  - ssh
  - ssh + slurm
- Document supported vs unsupported features for preflight validation.

Deliverables:
- README updates
- Spec docs + examples

## Execution Flow (High-Level)
1) Load TOML spec.
2) Validate spec (report supported/unsupported).
3) Expand parameter sets deterministically using seed.
4) Plan jobs across targets.
5) Stage spec + manifest + runner script to target.
6) Execute via Local/SSH/Slurm runner.
7) Emit heartbeats, enforce timeouts, and aggregate status in monitor.
8) Collect results and logs into structured output dirs.

## Non-Goals
- GUI orchestration or interactive AEDT sessions.
- Custom DSL beyond standard TOML.
- Implicit defaults hidden from documentation.

## Risks
- AEDT license availability across multiple machines.
- SSH/Slurm configuration differences across environments.
- Determinism drift if random sources are not fully controlled.
- High concurrency failures and monitor scalability under 500+ jobs.
- Hanging AEDT processes that require enforced timeouts/cleanup.

## Testing Strategy
- Pure-Python tests for spec parser/validator.
- Determinism tests for parameter expansion and dataset sampling.
- Optional integration tests requiring AEDT (skipped by default).

## Versioning
- Consider spec version bumps for new parameters.
- Maintain a simple backward-compatibility policy in spec docs.

## Divide and Conquer
- Track A: Spec/Determinism/Config + Execution (active focus).
- Track B: Backend/Monitoring/Docs (later phase).

## Current Focus
- Prioritize Spec/Determinism/Config + local execution.
- Defer remote execution (SSH/Slurm) and monitoring to a later phase.

## Todo List
- Define Python execution config fields for targets, slurm strategy (srun), and per-machine process limits.
- Implement TOML loader for design metadata and manifest generation (execution config stays in Python).
- Add deterministic TOML hash + friendly unique name mapping
  (adjective + scholar + hash prefix first two chars as suffix).
- Wire Fabric-based SSH execution for remote and Slurm modes (later phase).
- Document the monitor data grid fields and how to populate process snapshots (later phase).

## Next Steps (Suggested)
- Draft the Python execution config schema and document it.
- Implement a minimal LocalRunner + manifest format.
- Add a deterministic parameter expansion test.
- Create an example TOML that uses a local target.
- Define the monitoring/timeout config in the spec docs and add a CLI status prototype.
