#pragma once

#include <array>
#include <filesystem>
#include <string>
#include <vector>

#include <nlohmann/json.hpp>

namespace pf {

nlohmann::json read_json_file(const std::filesystem::path& path);

const nlohmann::json& require_key(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context);

std::string require_string(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context);

int require_int(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context);

double require_number(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context);

std::array<double, 3> require_vec3(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context);

std::vector<std::string> require_string_array(
    const nlohmann::json& object,
    const std::string& key,
    const std::string& context);

}  // namespace pf
