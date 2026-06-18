#!/usr/bin/env bash
# Drop into the forked-Palace dev/build container with the repo mounted and
# the GPU attached. Use this to build/patch the Palace fork and run palace.
#
#   ./docker/shell.sh                 # interactive bash in peetsfea-palace:dev
#   ./docker/shell.sh palace --help   # run a command directly
#
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd "${here}/../.." && pwd)"
image="${IMAGE:-peetsfea-palace:dev}"

if [ "$#" -eq 0 ]; then
  exec docker run --rm -it --gpus all --entrypoint /bin/bash \
    -v "${repo}:/work" -w /work "${image}" -l
fi
exec docker run --rm --gpus all --entrypoint /bin/bash \
  -v "${repo}:/work" -w /work "${image}" -lc 'exec "$@"' -- "$@"
