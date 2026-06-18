#include "cuda_probe.hpp"

#include <cuda_runtime.h>

namespace pf {

CudaStatus probe_cuda() {
  CudaStatus s;

  int count = 0;
  const cudaError_t count_err = cudaGetDeviceCount(&count);
  if (count_err != cudaSuccess) {
    s.runtime_ok = false;
    s.error = cudaGetErrorString(count_err);
    return s;
  }

  s.runtime_ok = true;
  s.device_count = count;
  if (count == 0) {
    return s;
  }

  cudaDeviceProp prop{};
  if (cudaGetDeviceProperties(&prop, 0) == cudaSuccess) {
    s.device_name = prop.name;
  }

  size_t free_bytes = 0;
  size_t total_bytes = 0;
  if (cudaSetDevice(0) == cudaSuccess &&
      cudaMemGetInfo(&free_bytes, &total_bytes) == cudaSuccess) {
    s.device_free_bytes = free_bytes;
    s.device_total_bytes = total_bytes;
  }

  return s;
}

} // namespace pf
