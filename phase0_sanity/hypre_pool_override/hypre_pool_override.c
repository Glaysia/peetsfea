#include <stddef.h>
#include <stdio.h>

#include "HYPRE_utilities.h"

__attribute__((constructor)) static void peetsfea_phase0_set_hypre_pool_sizes(void)
{
  const size_t device_pool_bytes = 512ULL * 1024ULL * 1024ULL;
  const size_t unified_pool_bytes = 512ULL * 1024ULL * 1024ULL;
  const size_t pinned_pool_bytes = 64ULL * 1024ULL * 1024ULL;

  const HYPRE_Int device_status = HYPRE_SetUmpireDevicePoolSize(device_pool_bytes);
  const HYPRE_Int unified_status = HYPRE_SetUmpireUMPoolSize(unified_pool_bytes);
  const HYPRE_Int pinned_status = HYPRE_SetUmpirePinnedPoolSize(pinned_pool_bytes);

  fprintf(stderr,
          "[peetsfea-phase0] HYPRE Umpire pool override: device=%zu unified=%zu "
          "pinned=%zu status=(%d,%d,%d)\n",
          device_pool_bytes, unified_pool_bytes, pinned_pool_bytes,
          (int)device_status, (int)unified_status, (int)pinned_status);
}
