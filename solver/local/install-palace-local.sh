#!/usr/bin/env bash
# Install a locally-runnable, docker/podman-wrapped Palace.
#
#   ./install-palace-local.sh wrapper   # install ~/.local/bin/palace only (fast)
#   ./install-palace-local.sh build     # build the selected image (heavy)
#   ./install-palace-local.sh all       # build + install wrapper
#
# Result: `palace <config.json>` works from the shell. The local default is
# Docker image peetsfea-palace:0.16.1pfterm01; stock palace:0.16.1 can still be selected
# explicitly for no-ferrite regression diagnostics.
#
# The fork's patched engine tag uses up to eight suffix characters after 0.16.1.
# Current default: 0.16.1pfterm01 = peetsfea terminal-source fork v01.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
solver="$(cd "${here}/.." && pwd)"
runtime="${PFSOLVER_CONTAINER_RUNTIME:-docker}"
image="${PFSOLVER_PALACE_IMAGE:-peetsfea-palace:0.16.1pfterm01}"
target="${1:-all}"

build_image() {
  # Stock 0.16.1 = the solver/palace build-baseline ref before forked magnetic
  # loss patches. It carries local Spack packaging needed by this Dockerfile but
  # no solver physics patch.
  command -v "${runtime}" >/dev/null || { echo "FATAL: ${runtime} not found" >&2; exit 2; }
  [ -e "${solver}/palace/CMakeLists.txt" ] || {
    echo "FATAL: solver/palace submodule not checked out (run: git submodule update --init solver/palace)" >&2
    exit 2; }
  build_context="${solver}"
  build_args=()
  temp_context=""
  if [ "${image}" = "palace:0.16.1" ] || [ "${image}" = "localhost/palace:0.16.1" ]; then
    stock_ref="${PFSOLVER_PALACE_STOCK_REF:-d2b68b6ba0b5834a9c3c6acc01caf13a9fa6a947}"
    stock_commit="$(git -C "${solver}/palace" rev-parse "${stock_ref}^{commit}")"
    temp_context="$(mktemp -d)"
    trap 'if [ -n "${temp_context:-}" ]; then rm -rf "${temp_context}"; fi' EXIT
    cp -a "${solver}/docker" "${temp_context}/docker"
    mkdir -p "${temp_context}/palace"
    git -C "${solver}/palace" archive --format=tar "${stock_commit}" | tar -C "${temp_context}/palace" -xf -
    build_context="${temp_context}"
    build_args+=(
      --build-arg "PEETSFEA_PALACE_FORK_VERSION=0.16.1"
      --build-arg "PEETSFEA_PALACE_SOURCE_COMMIT=${stock_commit}"
    )
  else
    source_commit="$(git -C "${solver}/palace" rev-parse HEAD)"
    if ! git -C "${solver}/palace" diff --quiet || ! git -C "${solver}/palace" diff --cached --quiet; then
      source_commit="${source_commit}-dirty"
    fi
    build_args+=(
      --build-arg "PEETSFEA_PALACE_FORK_VERSION=0.16.1pfterm01"
      --build-arg "PEETSFEA_PALACE_SOURCE_COMMIT=${source_commit}"
    )
  fi
  echo "building ${image} via ${runtime} (heavy; spack builds Palace deps)…"
  # Dockerfile uses SHELL ["/bin/bash","-lc"] + `source`; podman's default OCI
  # format ignores SHELL and runs RUN under /bin/sh (source -> exit 127).
  # --format docker makes podman honor the SHELL directive. docker needs no flag.
  fmt=()
  [ "${runtime}" = "podman" ] && fmt=(--format docker)
  "${runtime}" build "${fmt[@]}" "${build_args[@]}" -f "${build_context}/docker/Dockerfile.base" -t "${image}" "${build_context}"
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
