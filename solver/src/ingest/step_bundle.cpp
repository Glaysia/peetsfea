#include "ingest/step_bundle.hpp"

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <optional>
#include <set>
#include <sstream>
#include <string>

#include <toml++/toml.hpp>

#include "error.hpp"
#include "ingest/json_util.hpp"

namespace pf {
namespace {

std::filesystem::path require_file(
    const std::filesystem::path& path,
    const std::string& label) {
  if (!std::filesystem::is_regular_file(path)) {
    fail("required " + label + " file does not exist: " + path.string());
  }
  return path;
}

std::filesystem::path repo_materials_path() {
  const std::filesystem::path path = std::filesystem::current_path() / "solver" / "data" / "materials.toml";
  return require_file(path, "materials");
}

std::set<std::string> as_set(const std::vector<std::string>& values, const std::string& context) {
  std::set<std::string> out;
  for (const std::string& value : values) {
    const bool inserted = out.insert(value).second;
    if (!inserted) {
      fail(context + " contains duplicate name " + value);
    }
  }
  return out;
}

void require_contains(
    const std::set<std::string>& values,
    const std::string& value,
    const std::string& context) {
  if (values.find(value) == values.end()) {
    fail(context + " does not contain required value " + value);
  }
}

std::string material_key_for_ledger(const std::string& material) {
  if (material == "mull_ferrite" || material == "MULL12060ferrite") {
    return "ferrite";
  }
  return material;
}

std::array<std::array<double, 3>, 2> parse_segment(
    const nlohmann::json& value,
    const std::string& context) {
  if (!value.is_array() || value.size() != 2) {
    fail(context + " must contain exactly two endpoint vectors");
  }
  std::array<std::array<double, 3>, 2> out{};
  for (std::size_t i = 0; i < out.size(); ++i) {
    const nlohmann::json& point = value.at(i);
    if (!point.is_array() || point.size() != 3) {
      fail(context + "[" + std::to_string(i) + "] must be a 3-vector");
    }
    for (std::size_t axis = 0; axis < out.at(i).size(); ++axis) {
      if (!point.at(axis).is_number()) {
        fail(context + "[" + std::to_string(i) + "][" + std::to_string(axis) + "] must be numeric");
      }
      out.at(i).at(axis) = point.at(axis).get<double>();
    }
  }
  return out;
}

std::array<std::array<std::array<double, 3>, 2>, 2> parse_edge_vertices(
    const nlohmann::json& object,
    const std::string& context) {
  const nlohmann::json& value = require_key(object, "edge_vertices_xyz", context);
  if (!value.is_array() || value.size() != 2) {
    fail(context + ".edge_vertices_xyz must contain exactly two edge segments");
  }
  return {parse_segment(value.at(0), context + ".edge_vertices_xyz[0]"),
          parse_segment(value.at(1), context + ".edge_vertices_xyz[1]")};
}

const toml::table& require_table(
    const toml::table& table,
    const std::string& key,
    const std::string& context) {
  const toml::node* node = table.get(key);
  if (node == nullptr) {
    fail(context + " is missing required table " + key);
  }
  const toml::table* child = node->as_table();
  if (child == nullptr) {
    fail(context + "." + key + " must be a TOML table");
  }
  return *child;
}

const toml::array& require_array(
    const toml::table& table,
    const std::string& key,
    const std::string& context) {
  const toml::node* node = table.get(key);
  if (node == nullptr) {
    fail(context + " is missing required array " + key);
  }
  const toml::array* array = node->as_array();
  if (array == nullptr) {
    fail(context + "." + key + " must be a TOML array");
  }
  return *array;
}

std::string require_toml_string(
    const toml::table& table,
    const std::string& key,
    const std::string& context) {
  const toml::node* node = table.get(key);
  if (node == nullptr) {
    fail(context + " is missing required string " + key);
  }
  const std::optional<std::string> value = node->value<std::string>();
  if (!value.has_value() || value.value().empty()) {
    fail(context + "." + key + " must be a non-empty TOML string");
  }
  return value.value();
}

double require_toml_number(
    const toml::table& table,
    const std::string& key,
    const std::string& context) {
  const toml::node* node = table.get(key);
  if (node == nullptr) {
    fail(context + " is missing required number " + key);
  }
  if (const std::optional<double> value = node->value<double>(); value.has_value()) {
    return value.value();
  }
  if (const std::optional<int64_t> value = node->value<int64_t>(); value.has_value()) {
    return static_cast<double>(value.value());
  }
  fail(context + "." + key + " must be numeric");
}

double toml_number_or_zero(
    const toml::table& table,
    const std::string& key,
    const std::string& context) {
  const toml::node* node = table.get(key);
  if (node == nullptr) {
    return 0.0;
  }
  if (const std::optional<double> value = node->value<double>(); value.has_value()) {
    return value.value();
  }
  if (const std::optional<int64_t> value = node->value<int64_t>(); value.has_value()) {
    return static_cast<double>(value.value());
  }
  fail(context + "." + key + " must be numeric");
}

bool fixed_range_bool(
    const toml::table& root,
    const std::string& section,
    const std::string& key,
    const std::string& context) {
  const toml::table& section_table = require_table(root, section, context);
  const toml::table& value_table = require_table(section_table, key, context + "." + section);
  const toml::array& range = require_array(value_table, "range", context + "." + section + "." + key);
  if (range.size() != 4) {
    fail(context + "." + section + "." + key + ".range must have four entries");
  }
  const toml::node* lower_node = range.get(1);
  const toml::node* upper_node = range.get(2);
  const toml::node* count_node = range.get(3);
  if (lower_node == nullptr || upper_node == nullptr || count_node == nullptr) {
    fail(context + "." + section + "." + key + ".range is malformed");
  }
  const std::optional<int64_t> lower = lower_node->value<int64_t>();
  const std::optional<int64_t> upper = upper_node->value<int64_t>();
  const std::optional<int64_t> count = count_node->value<int64_t>();
  if (!lower.has_value() || !upper.has_value() || !count.has_value()) {
    fail(context + "." + section + "." + key + ".range bool field must use integer bounds");
  }
  if (count.value() != 1 || lower.value() != upper.value()) {
    fail(context + "." + section + "." + key + ".range must be a fixed point");
  }
  if (lower.value() != 0 && lower.value() != 1) {
    fail(context + "." + section + "." + key + ".range fixed value must be 0 or 1");
  }
  return lower.value() == 1;
}

toml::table parse_toml_file(const std::filesystem::path& path) {
  try {
    return toml::parse_file(path.string());
  } catch (const toml::parse_error& exc) {
    std::ostringstream os;
    os << "failed to parse TOML file " << path << ": " << exc.description();
    fail(os.str());
  }
}

std::filesystem::path design_toml_path(
    const std::filesystem::path& bundle_dir,
    const std::string& design_id) {
  if (design_id.empty()) {
    fail("port ledger design_id must be non-empty before resolving design TOML");
  }
  return require_file(bundle_dir / (design_id + ".toml"), "design TOML");
}

MaterialDb load_material_db(const std::filesystem::path& material_path) {
  const toml::table root = parse_toml_file(material_path);
  MaterialDb db;
  const toml::table& meta = require_table(root, "meta", material_path.string());
  db.frequency_hz = require_toml_number(meta, "frequency_hz", "materials.meta");

  for (const auto& entry : root) {
    const auto& key_view = entry.first;
    const toml::node& node = entry.second;
    const std::string key(key_view.str());
    if (key == "meta") {
      continue;
    }
    const toml::table* table = node.as_table();
    if (table == nullptr) {
      fail("materials." + key + " must be a table");
    }
    Material material;
    material.key = key;
    material.role = require_toml_string(*table, "role", "materials." + key);
    if (key == "ferrite") {
      material.eps_r = require_toml_number(*table, "eps_r", "materials.ferrite");
      material.mu_r_re = require_toml_number(*table, "mu_r_real_at_6p78MHz", "materials.ferrite");
      material.mu_r_im = require_toml_number(*table, "mu_r_imag_at_6p78MHz", "materials.ferrite");
      material.tan_d_m =
          require_toml_number(*table, "magnetic_loss_tangent_at_6p78MHz", "materials.ferrite");
      material.sigma = require_toml_number(*table, "conductivity", "materials.ferrite");
      material.dispersive = true;
    } else {
      material.eps_r = toml_number_or_zero(*table, "eps_r", "materials." + key);
      if (material.eps_r == 0.0) material.eps_r = 1.0;
      material.mu_r_re = toml_number_or_zero(*table, "mu_r", "materials." + key);
      if (material.mu_r_re == 0.0) material.mu_r_re = 1.0;
      material.sigma = toml_number_or_zero(*table, "conductivity", "materials." + key);
      material.tan_d_e = toml_number_or_zero(*table, "dielectric_loss_tangent", "materials." + key);
      material.tan_d_m = toml_number_or_zero(*table, "magnetic_loss_tangent", "materials." + key);
    }
    const bool inserted = db.materials.emplace(key, material).second;
    if (!inserted) {
      fail("duplicate material key " + key);
    }
  }
  return db;
}

DesignInfo load_design_info(const std::filesystem::path& design_path) {
  const toml::table root = parse_toml_file(design_path);
  DesignInfo info;
  info.path = design_path.string();
  info.spec_version = require_toml_string(root, "spec_version", design_path.string());
  info.schema_id = require_toml_string(root, "schema_id", design_path.string());
  const toml::table& design = require_table(root, "design", design_path.string());
  info.units = require_toml_string(design, "units", "design");
  info.tx_mull_enabled = fixed_range_bool(root, "ferrite", "tx_mull_is_enabled", design_path.string());
  info.rx_mull_enabled = fixed_range_bool(root, "ferrite", "rx_mull_is_enabled", design_path.string());
  return info;
}

TokenInfo load_token_info(const std::filesystem::path& token_path) {
  const toml::table root = parse_toml_file(token_path);
  const toml::table& metadata = require_table(root, "metadata", token_path.string());
  TokenInfo info;
  info.path = token_path.string();
  info.format = require_toml_string(metadata, "format", "token.metadata");
  info.schema_id = require_toml_string(metadata, "schema_id", "token.metadata");
  info.spec_version = require_toml_string(metadata, "spec_version", "token.metadata");
  info.seed = static_cast<int>(require_toml_number(metadata, "seed", "token.metadata"));
  info.action_count = static_cast<int>(require_toml_number(metadata, "action_count", "token.metadata"));
  const toml::array& actions = require_array(root, "actions", token_path.string());
  if (static_cast<int>(actions.size()) != info.action_count) {
    fail("token action_count does not match [[actions]] size");
  }
  return info;
}

void validate_body_lists(
    const std::vector<Body>& bodies,
    const std::set<std::string>& copper,
    const std::set<std::string>& fr4,
    const std::set<std::string>& ferrite,
    const std::set<std::string>& non_model) {
  std::set<std::string> seen;
  for (const Body& body : bodies) {
    const bool inserted = seen.insert(body.id).second;
    if (!inserted) {
      fail("duplicate body id " + body.id);
    }
    if (body.role == Role::Copper) {
      require_contains(copper, body.id, "copper_body_names");
    } else if (body.role == Role::Fr4) {
      require_contains(fr4, body.id, "fr4_body_names");
    } else if (body.role == Role::Ferrite) {
      require_contains(ferrite, body.id, "ferrite_body_names");
    } else if (body.role == Role::NonModel) {
      require_contains(non_model, body.id, "non_model_body_names");
    }
  }
  const auto require_all_seen = [&seen](const std::set<std::string>& names, const std::string& label) {
    for (const std::string& name : names) {
      require_contains(seen, name, label);
    }
  };
  require_all_seen(copper, "bodies");
  require_all_seen(fr4, "bodies");
  require_all_seen(ferrite, "bodies");
  require_all_seen(non_model, "bodies");
}

}  // namespace

Scene load_scene_bundle(const std::filesystem::path& bundle_dir) {
  if (!std::filesystem::is_directory(bundle_dir)) {
    fail("bundle directory does not exist: " + bundle_dir.string());
  }

  Scene scene;
  scene.bundle_dir = bundle_dir.string();
  const std::filesystem::path scene_step_path = require_file(bundle_dir / "ssw_scene.step", "STEP");
  const std::filesystem::path step_ledger_path =
      require_file(bundle_dir / "ssw_step_ledger.json", "step ledger");
  const std::filesystem::path port_ledger_path =
      require_file(bundle_dir / "ssw_aedt_port_ledger.json", "port ledger");
  const std::filesystem::path token_path = require_file(bundle_dir / "coil_making_token.toml", "token");
  const std::filesystem::path materials_path = repo_materials_path();

  scene.scene_step_path = scene_step_path.string();
  scene.step_ledger_path = step_ledger_path.string();
  scene.port_ledger_path = port_ledger_path.string();
  scene.token_path = token_path.string();
  scene.material_path = materials_path.string();

  const nlohmann::json step_ledger = read_json_file(step_ledger_path);
  const nlohmann::json port_ledger = read_json_file(port_ledger_path);

  scene.units = require_string(step_ledger, "units", "ssw_step_ledger");
  if (scene.units != "mm") {
    fail("ssw_step_ledger.units must be mm (actual=" + scene.units + ")");
  }
  const std::string port_units = require_string(port_ledger, "units", "ssw_aedt_port_ledger");
  if (port_units != scene.units) {
    fail("port ledger units do not match step ledger units");
  }
  scene.seed = require_int(step_ledger, "seed", "ssw_step_ledger");
  scene.design_id = require_string(port_ledger, "design_id", "ssw_aedt_port_ledger");

  const std::set<std::string> copper =
      as_set(require_string_array(step_ledger, "copper_body_names", "ssw_step_ledger"), "copper_body_names");
  const std::set<std::string> fr4 =
      as_set(require_string_array(step_ledger, "fr4_body_names", "ssw_step_ledger"), "fr4_body_names");
  const std::set<std::string> ferrite =
      as_set(require_string_array(step_ledger, "ferrite_body_names", "ssw_step_ledger"), "ferrite_body_names");
  const std::set<std::string> non_model = as_set(
      require_string_array(step_ledger, "non_model_body_names", "ssw_step_ledger"), "non_model_body_names");

  const nlohmann::json& raw_bodies = require_key(step_ledger, "bodies", "ssw_step_ledger");
  if (!raw_bodies.is_array()) {
    fail("ssw_step_ledger.bodies must be an array");
  }
  scene.bodies.reserve(raw_bodies.size());
  for (std::size_t i = 0; i < raw_bodies.size(); ++i) {
    const nlohmann::json& raw_body = raw_bodies.at(i);
    const std::string context = "ssw_step_ledger.bodies[" + std::to_string(i) + "]";
    Body body;
    body.id = require_string(raw_body, "object_id", context);
    body.role = parse_role(require_string(raw_body, "role", context), context);
    body.material = require_string(raw_body, "material", context);
    body.material_key = material_key_for_ledger(body.material);
    body.center_mm = require_vec3(raw_body, "center_xyz", context);
    body.size_mm = require_vec3(raw_body, "size_xyz", context);
    scene.bodies.push_back(body);
  }
  validate_body_lists(scene.bodies, copper, fr4, ferrite, non_model);

  const std::filesystem::path design_path = design_toml_path(bundle_dir, scene.design_id);
  scene.design = load_design_info(design_path);
  if (scene.design.units != scene.units) {
    fail("design TOML units do not match ledger units");
  }
  scene.token = load_token_info(token_path);
  if (scene.token.seed != scene.seed) {
    fail("token seed does not match step ledger seed");
  }
  scene.material_db = load_material_db(materials_path);

  for (const Body& body : scene.bodies) {
    if (scene.material_db.materials.find(body.material_key) == scene.material_db.materials.end()) {
      fail("body " + body.id + " references undefined material " + body.material +
           " (resolved key " + body.material_key + ")");
    }
  }

  scene.ferrite_enabled = scene.design.tx_mull_enabled || scene.design.rx_mull_enabled;
  const bool has_ferrite_body = !ferrite.empty();
  if (scene.ferrite_enabled != has_ferrite_body) {
    fail("ferrite enable flag and ferrite bodies disagree");
  }

  const nlohmann::json& raw_ports = require_key(port_ledger, "port_edges", "ssw_aedt_port_ledger");
  if (!raw_ports.is_array()) {
    fail("ssw_aedt_port_ledger.port_edges must be an array");
  }
  if (raw_ports.size() != 2) {
    fail("ssw_aedt_port_ledger.port_edges must contain exactly tx 1 + rx 1");
  }
  int tx_count = 0;
  int rx_count = 0;
  scene.ports.reserve(raw_ports.size());
  for (std::size_t i = 0; i < raw_ports.size(); ++i) {
    const nlohmann::json& raw_port = raw_ports.at(i);
    const std::string context = "ssw_aedt_port_ledger.port_edges[" + std::to_string(i) + "]";
    PortEdge port;
    port.role = require_string(raw_port, "role", context);
    if (port.role == "tx") {
      ++tx_count;
    } else if (port.role == "rx") {
      ++rx_count;
    } else {
      fail(context + ".role must be tx or rx");
    }
    port.copper_body = require_string(raw_port, "copper_body_name", context);
    require_contains(copper, port.copper_body, "copper_body_names");
    const auto edge = parse_edge_vertices(raw_port, context);
    port.seg_a = edge.at(0);
    port.seg_b = edge.at(1);
    scene.ports.push_back(port);
  }
  if (tx_count != 1 || rx_count != 1) {
    fail("port_edges must contain exactly one tx and one rx");
  }

  return scene;
}

nlohmann::json scene_to_json(const Scene& scene) {
  nlohmann::json root;
  root["schema"] = "peetsfea.pfsolver.inspect.v1";
  root["bundle_dir"] = scene.bundle_dir;
  root["design_id"] = scene.design_id;
  root["units"] = scene.units;
  root["seed"] = scene.seed;
  root["paths"] = {
      {"scene_step", scene.scene_step_path},
      {"step_ledger", scene.step_ledger_path},
      {"port_ledger", scene.port_ledger_path},
      {"token", scene.token_path},
      {"design_toml", scene.design.path},
      {"materials", scene.material_path},
  };
  root["freq"] = {{"single", true}, {"f0_hz", scene.material_db.frequency_hz}};
  root["ferrite_enabled"] = scene.ferrite_enabled;
  root["token"] = {
      {"format", scene.token.format},
      {"schema_id", scene.token.schema_id},
      {"spec_version", scene.token.spec_version},
      {"seed", scene.token.seed},
      {"action_count", scene.token.action_count},
  };
  root["design"] = {
      {"spec_version", scene.design.spec_version},
      {"schema_id", scene.design.schema_id},
      {"units", scene.design.units},
      {"tx_mull_enabled", scene.design.tx_mull_enabled},
      {"rx_mull_enabled", scene.design.rx_mull_enabled},
  };

  nlohmann::json bodies = nlohmann::json::array();
  nlohmann::json role_counts = {{"copper", 0}, {"fr4", 0}, {"ferrite", 0}, {"non_model", 0}};
  for (const Body& body : scene.bodies) {
    const std::string role = role_name(body.role);
    role_counts[role] = role_counts[role].get<int>() + 1;
    bodies.push_back({
        {"id", body.id},
        {"role", role},
        {"material", body.material},
        {"material_key", body.material_key},
        {"center_mm", body.center_mm},
        {"size_mm", body.size_mm},
    });
  }
  root["body_count"] = scene.bodies.size();
  root["role_counts"] = role_counts;
  root["bodies"] = bodies;

  nlohmann::json ports = nlohmann::json::array();
  for (const PortEdge& port : scene.ports) {
    ports.push_back({
        {"role", port.role},
        {"copper_body", port.copper_body},
        {"edge_vertices_xyz", {port.seg_a, port.seg_b}},
    });
  }
  root["ports"] = ports;

  nlohmann::json materials = nlohmann::json::object();
  for (const auto& entry : scene.material_db.materials) {
    const Material& material = entry.second;
    materials[entry.first] = {
        {"role", material.role},
        {"eps_r", material.eps_r},
        {"mu_r_re", material.mu_r_re},
        {"mu_r_im", material.mu_r_im},
        {"sigma", material.sigma},
        {"tan_d_e", material.tan_d_e},
        {"tan_d_m", material.tan_d_m},
        {"dispersive", material.dispersive},
    };
  }
  root["materials"] = materials;
  return root;
}

void print_scene_summary(const Scene& scene) {
  const nlohmann::json as_json = scene_to_json(scene);
  const nlohmann::json& role_counts = as_json.at("role_counts");
  std::cout << "pfsolver inspect\n";
  std::cout << "bundle      : " << scene.bundle_dir << "\n";
  std::cout << "design_id   : " << scene.design_id << "\n";
  std::cout << "units       : " << scene.units << "\n";
  std::cout << "frequency   : " << scene.material_db.frequency_hz << " Hz\n";
  std::cout << "bodies      : " << scene.bodies.size() << " (copper "
            << role_counts.at("copper").get<int>() << ", fr4 " << role_counts.at("fr4").get<int>()
            << ", ferrite " << role_counts.at("ferrite").get<int>() << ", non_model "
            << role_counts.at("non_model").get<int>() << ")\n";
  std::cout << "ports       : " << scene.ports.size() << " (";
  for (std::size_t i = 0; i < scene.ports.size(); ++i) {
    if (i != 0) std::cout << ", ";
    std::cout << scene.ports.at(i).role << "->" << scene.ports.at(i).copper_body;
  }
  std::cout << ")\n";
  std::cout << "ferrite     : " << (scene.ferrite_enabled ? "enabled" : "disabled") << "\n";
}

}  // namespace pf
