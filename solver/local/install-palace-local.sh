#!/usr/bin/env bash
# Install a locally-runnable, podman/docker-wrapped Palace 0.16.1 (stock).
#
#   ./install-palace-local.sh wrapper   # install ~/.local/bin/palace only (fast)
#   ./install-palace-local.sh build     # build the palace:0.16.1 image (heavy)
#   ./install-palace-local.sh all       # build + install wrapper
#
# Result: `palace <config.json>` works from the shell, running stock released
# Palace 0.16.1 in a container — pfsolver (and Codex) call it as if local, the
# way pyaedt calls the podman-wrapped ansysedt.
#
# The fork's patched engine (magnetic loss) is version 0.16.1pfs and is built
# separately as palace:0.16.1pfs; point the wrapper at it with
# PFSOLVER_PALACE_IMAGE=palace:0.16.1pfs.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
solver="$(cd "${here}/.." && pwd)"
runtime="${PFSOLVER_CONTAINER_RUNTIME:-podman}"
image="${PFSOLVER_PALACE_IMAGE:-palace:0.16.1}"
target="${1:-all}"

build_image() {
  # Stock 0.16.1 = the solver/palace submodule at its v0.16.1 tag (no fork
  # magnetic-loss patches yet). Built in-tree by docker/Dockerfile.base.
  command -v "${runtime}" >/dev/null || { echo "FATAL: ${runtime} not found" >&2; exit 2; }
  [ -e "${solver}/palace/CMakeLists.txt" ] || {
    echo "FATAL: solver/palace submodule not checked out (run: git submodule update --init solver/palace)" >&2
    exit 2; }
  echo "building ${image} via ${runtime} (heavy; spack builds Palace deps)…"
  "${runtime}" build -f "${solver}/docker/Dockerfile.base" -t "${image}" "${solver}"
  echo "built: ${image}"
}

install_wrapper() {
  mkdir -p "${HOME}/.local/bin"
  install -m 0755 "${here}/palace-local-wrapper.sh" "${HOME}/.local/bin/palace"
  echo "installed: ${HOME}/.local/bin/palace  (image=${image}, runtime=${runtime})"
  case ":${PATH}:" in *":${HOME}/.local/bin:"*) ;; *)
    echo "note: add ~/.local/bin to PATH" >&2 ;;
  esac
}

case "${target}" in
  wrapper) install_wrapper ;;
  build)   build_image ;;
  all)     build_image; install_wrapper ;;
  *) echo "usage: $0 {wrapper|build|all}" >&2; exit 2 ;;
esac
