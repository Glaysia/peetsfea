#!/usr/bin/env bash
# Build the forked-Palace CUDA dev/build image (the FEM engine).
#
# pfsolver itself is a Python orchestrator (runs outside Docker, in the
# peetsfea ecosystem). The only thing containerized is the forked Palace
# engine — like ansysedt behind pyaedt. This builds that engine image.
#
#   ./docker/build.sh           # build peetsfea-palace:dev from Dockerfile.base
#
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ctx="$(cd "${here}/.." && pwd)"   # build context = solver/

docker build -f "${here}/Dockerfile.base" -t peetsfea-palace:dev "${ctx}"
echo "built: peetsfea-palace:dev"
