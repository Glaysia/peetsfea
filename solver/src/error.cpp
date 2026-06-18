#include "error.hpp"

namespace pf {

[[noreturn]] void fail(const std::string& message) {
  throw PfError(message);
}

}  // namespace pf
