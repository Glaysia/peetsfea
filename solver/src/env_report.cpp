#include "env_report.hpp"

#include <cuda_runtime.h>
#include <mpi.h>

#include <sstream>

namespace pf {

std::string toolchain_report() {
  std::ostringstream os;

  os << "compiler      : ";
#if defined(__clang__)
  os << "clang " << __clang_major__ << "." << __clang_minor__;
#elif defined(__GNUC__)
  os << "gcc " << __GNUC__ << "." << __GNUC_MINOR__;
#else
  os << "unknown";
#endif
  os << "  (c++" << (__cplusplus / 100 % 100) << ")\n";

  os << "cuda runtime  : built against " << (CUDART_VERSION / 1000) << "."
     << (CUDART_VERSION / 10 % 100);
  int rt = 0;
  if (cudaRuntimeGetVersion(&rt) == cudaSuccess) {
    os << ", loaded " << (rt / 1000) << "." << (rt / 10 % 100);
  }
  int drv = 0;
  if (cudaDriverGetVersion(&drv) == cudaSuccess) {
    os << ", driver supports " << (drv / 1000) << "." << (drv / 10 % 100);
  }
  os << "\n";

  char mpi_lib[MPI_MAX_LIBRARY_VERSION_STRING] = {0};
  int mpi_len = 0;
  if (MPI_Get_library_version(mpi_lib, &mpi_len) == MPI_SUCCESS && mpi_len > 0) {
    // Keep only the first line; some libraries emit a multi-line banner.
    std::string lib(mpi_lib, static_cast<size_t>(mpi_len));
    const auto nl = lib.find('\n');
    if (nl != std::string::npos) lib.resize(nl);
    os << "mpi           : " << lib << "\n";
  } else {
    os << "mpi           : unknown\n";
  }

  return os.str();
}

} // namespace pf
