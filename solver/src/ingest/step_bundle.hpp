#pragma once

#include <filesystem>

#include <nlohmann/json.hpp>

#include "model/scene.hpp"

namespace pf {

Scene load_scene_bundle(const std::filesystem::path& bundle_dir);
nlohmann::json scene_to_json(const Scene& scene);
void print_scene_summary(const Scene& scene);

}  // namespace pf
