#!/usr/bin/env bash
# podman/docker-wrapped Palace — installed as ~/.local/bin/palace.
#
# pfsolver invokes `palace <config.json>` exactly as if Palace were a local
# binary; this wrapper runs it inside the container, the same way pyaedt drives
# the podman-wrapped ansysedt. It runs STOCK released Palace 0.16.1 (no fork
# magnetic-loss patches). The fork's patched engine is version 0.16.1pfs and
# uses a different image tag (PFSOLVER_PALACE_IMAGE).
#
# Runtime-agnostic by env:
#   PFSOLVER_CONTAINER_RUNTIME = podman (default) | docker
#   PFSOLVER_PALACE_IMAGE      = palace:0.16.1 (default; stock). fork → palace:0.16.1pfs
#   PFSOLVER_MPI_RANKS         = 4 (default)
#   PFSOLVER_WORKDIR           = $PWD (mounted at the same path so config/mesh
#                                paths stay valid)
# On an enroot cluster, do NOT use this wrapper — invoke via enroot/pyxis (see
# solver/local/README.md). The container runner is intentionally abstracted.
set -euo pipefail

IMAGE="${PFSOLVER_PALACE_IMAGE:-palace:0.16.1}"
RUNTIME="${PFSOLVER_CONTAINER_RUNTIME:-podman}"
RANKS="${PFSOLVER_MPI_RANKS:-4}"
workdir="${PFSOLVER_WORKDIR:-$PWD}"

case "${RUNTIME}" in
  podman) gpu=(--device nvidia.com/gpu=all) ;;   # NVIDIA CDI (/etc/cdi/nvidia.yaml)
  docker) gpu=(--gpus all) ;;
  *) echo "FATAL: unknown PFSOLVER_CONTAINER_RUNTIME=${RUNTIME} (podman|docker)" >&2; exit 2 ;;
esac

# CUDA mandatory: the image is CUDA-only; if no GPU is attached, palace fails.
exec "${RUNTIME}" run --rm "${gpu[@]}" \
  -v "${workdir}:${workdir}" -w "${workdir}" \
  "${IMAGE}" \
  /bin/bash -lc 'exec mpirun --allow-run-as-root -np "$0" palace "$@"' "${RANKS}" "$@"
