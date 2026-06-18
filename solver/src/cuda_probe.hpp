#pragma once
#include <string>

namespace pf {

struct CudaStatus {
  bool runtime_ok = false;       // cudaGetDeviceCount returned cudaSuccess
  int device_count = 0;          // visible CUDA devices
  std::string error;             // CUDA runtime error string, when runtime_ok == false
  std::string device_name;       // name of device 0, when available
  size_t device_total_bytes = 0; // total VRAM of device 0
  size_t device_free_bytes = 0;  // free VRAM of device 0
};

// Queries the CUDA runtime. Never throws; reports failure via CudaStatus.
CudaStatus probe_cuda();

} // namespace pf
