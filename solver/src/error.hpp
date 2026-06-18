#pragma once

#include <stdexcept>
#include <string>

namespace pf {

class PfError : public std::runtime_error {
 public:
  explicit PfError(const std::string& message) : std::runtime_error(message) {}
};

[[noreturn]] void fail(const std::string& message);

}  // namespace pf
