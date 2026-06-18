# pfsolver — peetsfea CUDA C++ FEM solver

Open-source, CUDA-mandatory, full-wave terminal-network FEM solver that replaces
Ansys HFSS for Z(f) extraction on peetsfea 0.3.7 geometry. Long-term plan:
[`../cpp-cuda-fem-solver-longterm-plan.html`](../cpp-cuda-fem-solver-longterm-plan.html).

## Non-negotiables
- **CUDA mandatory.** No CPU build, no CPU fallback. A toolchain without the CUDA
  toolkit fails to configure; a host without a CUDA device fails `doctor`.
- **Docker only.** There is no supported host build. Everything goes through the
  images in `docker/`.
- **Full-wave only.** HFSS-style full-wave driven terminal-network solve (Palace
  `Driven`). MQS / electrostatic / Q3D were rejected empirically.

## Quick start (verify the build environment now)
The toolchain image is self-contained (CUDA + MPI + CMake) and builds the current
`pfsolver` bootstrap CLI without the long Palace build:

```bash
cd solver
./docker/build.sh toolchain          # docker build -f docker/Dockerfile.toolchain
./docker/run.sh doctor               # docker run --rm --gpus all pfsolver:toolchain doctor
```

`doctor` reports compiler / CUDA / MPI and **exits non-zero if no CUDA device is
visible** — the CUDA-mandatory contract in executable form.

## Full FEM pipeline image (heavy, run once)
Builds CUDA-enabled Palace 0.16.0 from source via spack (tens of minutes):

```bash
cd solver
./docker/build.sh base               # peetsfea-solver-base:0.16.0  (Palace + gmsh)
./docker/build.sh app                # pfsolver:latest  (app on the base)
IMAGE=pfsolver:latest ./docker/run.sh doctor
```

Pinned to the phase0-validated build: `palace@0.16.0+cuda~slepc~sundials
cuda_arch=86`, base `spack/ubuntu-noble:develop`. Adjust `cuda_arch` for other
GPUs via `--build-arg PALACE_SPEC=...`.

## Layout
```
solver/
  CMakeLists.txt          # CUDA + MPI required; C++17
  src/
    main.cpp              # CLI: version | doctor
    cuda_probe.{hpp,cpp}  # CUDA runtime probe (device count / VRAM)
    env_report.{hpp,cpp}  # compiler / CUDA / MPI report
  docker/
    Dockerfile.toolchain  # fast self-contained CUDA build env
    Dockerfile.base       # heavy: CUDA Palace + mesher base
    Dockerfile            # app on top of the base
    build.sh  run.sh
```

## Status
Bootstrap. `pfsolver doctor` is the first executable contract. Next (Phase A of the
plan): 0.3.7 STEP/ledger/token ingest -> mesh -> Palace `Driven` config emit ->
port S/V/I -> terminal Z(f), against the solver-neutral output schema.

## VRAM note
On 8 GB cards (RTX 3070) default HYPRE/Umpire CUDA pools overshoot and abort with
`cudaMalloc ... out of memory`. The launcher will set VRAM-fitted pool sizes
(device/unified 512 MiB, pinned 64 MiB as a starting point); see
`../phase0_sanity/hypre_pool_override/`.
