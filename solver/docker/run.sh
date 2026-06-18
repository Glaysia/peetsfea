#!/usr/bin/env bash
# Run a pfsolver image with the GPU attached. CUDA is mandatory, so --gpus all
# is always passed; `doctor` will fail loudly if no device is visible.
#
#   ./docker/run.sh                 # pfsolver:toolchain doctor
#   ./docker/run.sh doctor
#   ./docker/run.sh version
#   IMAGE=pfsolver:latest ./docker/run.sh doctor
#
set -euo pipefail

image="${IMAGE:-pfsolver:toolchain}"
exec docker run --rm --gpus all "${image}" "$@"
