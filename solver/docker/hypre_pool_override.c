#include <errno.h>
#include <dlfcn.h>
#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

#include "HYPRE_utilities.h"

typedef HYPRE_Int (*peetsfea_hypre_initialize_fn)(void);

static int peetsfea_pool_sizes_applied = 0;

static size_t peetsfea_pool_size_from_env(const char *name, size_t fallback)
{
  const char *raw_value = getenv(name);
  if (raw_value == NULL || raw_value[0] == '\0') {
    return fallback;
  }

  errno = 0;
  char *end = NULL;
  const unsigned long long parsed = strtoull(raw_value, &end, 10);
  if (errno != 0 || end == raw_value || end[0] != '\0' || parsed == 0ULL || parsed > SIZE_MAX) {
    fprintf(stderr,
            "[peetsfea-palace] fatal: invalid %s=%s; expected a positive byte count\n",
            name, raw_value);
    abort();
  }
  return (size_t)parsed;
}

static void peetsfea_set_hypre_pool_sizes(void)
{
  if (peetsfea_pool_sizes_applied != 0) {
    return;
  }
  const size_t device_pool_bytes =
      peetsfea_pool_size_from_env("PEETSFEA_HYPRE_DEVICE_POOL_BYTES", 512ULL * 1024ULL * 1024ULL);
  const size_t unified_pool_bytes =
      peetsfea_pool_size_from_env("PEETSFEA_HYPRE_UNIFIED_POOL_BYTES", 512ULL * 1024ULL * 1024ULL);
  const size_t pinned_pool_bytes =
      peetsfea_pool_size_from_env("PEETSFEA_HYPRE_PINNED_POOL_BYTES", 64ULL * 1024ULL * 1024ULL);

  const HYPRE_Int device_status = HYPRE_SetUmpireDevicePoolSize(device_pool_bytes);
  const HYPRE_Int unified_status = HYPRE_SetUmpireUMPoolSize(unified_pool_bytes);
  const HYPRE_Int pinned_status = HYPRE_SetUmpirePinnedPoolSize(pinned_pool_bytes);

  fprintf(stderr,
          "[peetsfea-palace] HYPRE Umpire pool override: device=%zu unified=%zu "
          "pinned=%zu status=(%d,%d,%d)\n",
          device_pool_bytes, unified_pool_bytes, pinned_pool_bytes,
          (int)device_status, (int)unified_status, (int)pinned_status);
  if (device_status != 0 || unified_status != 0 || pinned_status != 0) {
    fprintf(stderr,
            "[peetsfea-palace] fatal: HYPRE Umpire pool override failed "
            "status=(%d,%d,%d)\n",
            (int)device_status, (int)unified_status, (int)pinned_status);
    abort();
  }
  peetsfea_pool_sizes_applied = 1;
}

HYPRE_Int HYPRE_Initialize(void)
{
  dlerror();
  peetsfea_hypre_initialize_fn real_hypre_initialize =
      (peetsfea_hypre_initialize_fn)dlsym(RTLD_NEXT, "HYPRE_Initialize");
  const char *dlsym_error = dlerror();
  if (dlsym_error != NULL || real_hypre_initialize == NULL) {
    fprintf(stderr,
            "[peetsfea-palace] fatal: failed to resolve real HYPRE_Initialize: %s\n",
            dlsym_error == NULL ? "unknown error" : dlsym_error);
    abort();
  }

  const HYPRE_Int initialize_status = real_hypre_initialize();
  if (initialize_status != 0) {
    fprintf(stderr,
            "[peetsfea-palace] fatal: HYPRE_Initialize failed status=%d\n",
            (int)initialize_status);
    abort();
  }
  peetsfea_set_hypre_pool_sizes();
  return initialize_status;
}
