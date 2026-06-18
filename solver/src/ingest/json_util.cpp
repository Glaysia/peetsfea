#include "ingest/json_util.hpp"

#include <fstream>

#include "error.hpp"

namespace pf {

nlohmann::json read_json_file(const std::filesystem::path& path) {
  if (!std::filesystem::is_regular_file(path)) {
    fail("required JSON file does not exist: " + path.string());
  }
  std::ifstream input(path);
  if (!input) {
    fail("failed to open JSON file: " + path.string());
  }
  try {
    nlohmann::json parsed;
    input >> parsed;
    if (!parsed.is_object()) {
      fail("JSON root must be an object: " + path.string());
    }
    return parsed;
  } catch (const nlohmann::json::exception& exc) {
    fail("failed to parse JSON file " + path.string() + ": " + exc.what());
  }
}

const nlohmann::json& require_key(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context) {
  if (!object.is_object()) {
    fail(context + " must be a JSON object");
  }
  if (!object.contains(key)) {
    fail(context + " is missing required key " + key);
  }
  return object.at(key);
}

std::string require_string(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context) {
  const nlohmann::json& value = require_key(object, key, context);
  if (!value.is_string()) {
    fail(context + "." + key + " must be a string");
  }
  const std::string result = value.get<std::string>();
  if (result.empty()) {
    fail(context + "." + key + " must be a non-empty string");
  }
  return result;
}

int require_int(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context) {
  const nlohmann::json& value = require_key(object, key, context);
  if (!value.is_number_integer()) {
    fail(context + "." + key + " must be an integer");
  }
  return value.get<int>();
}

double require_number(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context) {
  const nlohmann::json& value = require_key(object, key, context);
  if (!value.is_number()) {
    fail(context + "." + key + " must be numeric");
  }
  return value.get<double>();
}

std::array<double, 3> require_vec3(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context) {
  const nlohmann::json& value = require_key(object, key, context);
  if (!value.is_array() || value.size() != 3) {
    fail(context + "." + key + " must be an array of exactly 3 numbers");
  }
  std::array<double, 3> out{};
  for (std::size_t i = 0; i < out.size(); ++i) {
    if (!value.at(i).is_number()) {
      fail(context + "." + key + "[" + std::to_string(i) + "] must be numeric");
    }
    out.at(i) = value.at(i).get<double>();
  }
  return out;
}

std::vector<std::string> require_string_array(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context) {
  const nlohmann::json& value = require_key(object, key, context);
  if (!value.is_array()) {
    fail(context + "." + key + " must be an array");
  }
  std::vector<std::string> out;
  out.reserve(value.size());
  for (std::size_t i = 0; i < value.size(); ++i) {
    if (!value.at(i).is_string()) {
      fail(context + "." + key + "[" + std::to_string(i) + "] must be a string");
    }
    const std::string item = value.at(i).get<std::string>();
    if (item.empty()) {
      fail(context + "." + key + "[" + std::to_string(i) + "] must be non-empty");
    }
    out.push_back(item);
  }
  return out;
}

}  // namespace pf
