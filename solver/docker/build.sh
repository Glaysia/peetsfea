#!/usr/bin/env bash
# Build pfsolver Docker images. Docker-only by design; there is no host build.
#
#   ./docker/build.sh toolchain   # fast self-contained CUDA build env (verify)
#   ./docker/build.sh base        # heavy: CUDA Palace base (run once)
#   ./docker/build.sh app         # app on top of the Palace base
#
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ctx="$(cd "${here}/.." && pwd)"   # build context = solver/
target="${1:-toolchain}"

case "${target}" in
  toolchain)
    docker build -f "${here}/Dockerfile.toolchain" -t pfsolver:toolchain "${ctx}"
    ;;
  base)
    docker build -f "${here}/Dockerfile.base" -t peetsfea-solver-base:0.16.0 "${ctx}"
    ;;
  app)
    docker build -f "${here}/Dockerfile" -t pfsolver:latest "${ctx}"
    ;;
  *)
    echo "unknown target: ${target} (expected: toolchain | base | app)" >&2
    exit 2
    ;;
esac

echo "built: ${target}"
