#pragma once

#include <array>
#include <map>
#include <string>
#include <vector>

namespace pf {

enum class Role { Copper, Fr4, Ferrite, NonModel };

struct Body {
  std::string id;
  Role role;
  std::string material;
  std::string material_key;
  std::array<double, 3> center_mm;
  std::array<double, 3> size_mm;
};

struct PortEdge {
  std::string role;
  std::string copper_body;
  std::array<std::array<double, 3>, 2> seg_a;
  std::array<std::array<double, 3>, 2> seg_b;
};

struct Material {
  std::string key;
  std::string role;
  double eps_r = 1.0;
  double mu_r_re = 1.0;
  double mu_r_im = 0.0;
  double sigma = 0.0;
  double tan_d_e = 0.0;
  double tan_d_m = 0.0;
  bool dispersive = false;
};

struct MaterialDb {
  double frequency_hz = 6.78e6;
  std::map<std::string, Material> materials;
};

struct DesignInfo {
  std::string path;
  std::string spec_version;
  std::string schema_id;
  std::string units;
  bool tx_mull_enabled = false;
  bool rx_mull_enabled = false;
};

struct TokenInfo {
  std::string path;
  std::string format;
  std::string schema_id;
  std::string spec_version;
  int seed = 0;
  int action_count = 0;
};

struct Scene {
  std::string bundle_dir;
  std::string scene_step_path;
  std::string step_ledger_path;
  std::string port_ledger_path;
  std::string token_path;
  std::string material_path;
  std::string design_id;
  std::string units;
  int seed = 0;
  std::vector<Body> bodies;
  std::vector<PortEdge> ports;
  MaterialDb material_db;
  DesignInfo design;
  TokenInfo token;
  bool ferrite_enabled = false;
};

std::string role_name(Role role);
Role parse_role(const std::string& value, const std::string& context);

}  // namespace pf
