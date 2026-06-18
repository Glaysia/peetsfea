#include "model/scene.hpp"

#include "error.hpp"

namespace pf {

std::string role_name(Role role) {
  switch (role) {
    case Role::Copper:
      return "copper";
    case Role::Fr4:
      return "fr4";
    case Role::Ferrite:
      return "ferrite";
    case Role::NonModel:
      return "non_model";
  }
  fail("unsupported role enum value");
}

Role parse_role(const std::string& value, const std::string& context) {
  if (value == "copper") return Role::Copper;
  if (value == "fr4") return Role::Fr4;
  if (value == "ferrite") return Role::Ferrite;
  if (value == "non_model") return Role::NonModel;
  fail(context + " has unsupported role " + value);
}

}  // namespace pf
