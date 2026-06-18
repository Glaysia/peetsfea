#!/usr/bin/env bash
set -euo pipefail

palace_home="${PEETSFEA_PALACE_HOME:-/opt/peetsfea-palace}"
real_palace="${palace_home}/bin/palace"
override="${PEETSFEA_HYPRE_POOL_OVERRIDE:-${palace_home}/lib/libhypre_pool_override.so}"

if [ ! -x "${real_palace}" ]; then
  echo "FATAL: forked Palace wrapper cannot find executable: ${real_palace}" >&2
  exit 2
fi

if [ -f "${override}" ]; then
  export LD_PRELOAD="${override}${LD_PRELOAD:+:${LD_PRELOAD}}"
fi

exec "${real_palace}" "$@"
