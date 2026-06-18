#pragma once
#include <string>

namespace pf {

// Returns a human-readable report of the build/runtime toolchain
// (compiler, MPI, CUDA toolkit) used by this binary.
std::string toolchain_report();

} // namespace pf
