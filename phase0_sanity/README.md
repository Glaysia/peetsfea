# Palace CUDA Phase 0 Sanity Run

Status: passed with a GPU-only HYPRE pool-size override.

This directory records a GPU-only Palace sanity attempt. It does not modify the
peetsfea runtime, TOML schema, or backend code. It also does not vendor Palace
source into the repository.

What passed:

- Docker GPU passthrough with `nvidia/cuda:13.0.2-base-ubuntu24.04`.
- CUDA-enabled Palace build through Spack in the `spack/ubuntu-noble:develop`
  container.
- Palace startup with `Solver.Device = "GPU"` and CUDA backend selection.
- Official cylinder driven-wave example with GPU field output and `port-S.csv`
  after applying the HYPRE pool-size override.
- CPW LumpedPort one-frequency sanity run with `port-S.csv`, `port-V.csv`,
  `port-I.csv`, and Paraview field output after applying the same override.

What did not pass:

- Default Palace GPU runs without the pool-size override abort with CUDA OOM:
  `cudaMalloc( bytes = 4294967312 ) failed with error: out of memory`.
- The full upstream CPW frequency sweep still aborts later with CUDA OOM in the
  current desktop RTX 3070 session, although it produces partial port CSVs.
- No CPU fallback was attempted.

Primary evidence:

- `solver_manifest.json`
- `build_spack_install.log`
- `hypre_pool_override/hypre_pool_override.c`
- `hypre_pool_override/libhypre_pool_override.so`
- `palace_cylinder_gpu_hypre_pool_override_stdout.log`
- `palace_cpw_onefreq_gpu_hypre_pool_override_stdout.log`
- `input_sha256.txt`
- `cylinder_input_sha256.txt`
- `cpw/postpro/lumped_onefreq/port-S.csv`
- `cpw/postpro/lumped_onefreq/port-V.csv`
- `cpw/postpro/lumped_onefreq/port-I.csv`
- `cpw/postpro/lumped_onefreq/paraview/`

Current interpretation:

The container runtime and Palace CUDA binary are usable. On this 8 GB RTX 3070
desktop session, default HYPRE/Umpire CUDA allocation behavior is too aggressive
for the available free VRAM, so the reproducible Phase 0 GPU smoke path includes
an explicit pool-size override. The one-frequency CPW output is a smoke artifact,
not a physics-validation benchmark.
