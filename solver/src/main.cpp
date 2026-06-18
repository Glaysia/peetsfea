// pfsolver — peetsfea CUDA C++ FEM solver entrypoint.
//
// This is the bootstrap CLI for the solver build environment. It does not yet
// solve anything; it establishes the CUDA-mandatory contract and a place for
// the ingest -> mesh -> assemble -> solve -> post pipeline to grow into.
//
// Subcommands:
//   pfsolver version   print version and exit 0
//   pfsolver doctor    report toolchain + CUDA device state.
//                      Exit 0 only if at least one CUDA device is usable;
//                      exit non-zero otherwise (CUDA is mandatory, no fallback).

#include <cstring>
#include <exception>
#include <iostream>
#include <string>

#include "cuda_probe.hpp"
#include "env_report.hpp"
#include "error.hpp"
#include "ingest/step_bundle.hpp"

namespace {

#ifndef PFSOLVER_VERSION
#define PFSOLVER_VERSION "0.0.0"
#endif

std::string human_bytes(size_t bytes) {
  const double mib = static_cast<double>(bytes) / (1024.0 * 1024.0);
  char buf[64];
  std::snprintf(buf, sizeof(buf), "%.0f MiB", mib);
  return buf;
}

int cmd_version() {
  std::cout << "pfsolver " << PFSOLVER_VERSION << "\n";
  return 0;
}

int cmd_doctor() {
  std::cout << "pfsolver " << PFSOLVER_VERSION << " — doctor\n\n";
  std::cout << pf::toolchain_report() << "\n";

  const pf::CudaStatus cu = pf::probe_cuda();
  if (!cu.runtime_ok) {
    std::cerr << "cuda          : UNAVAILABLE (" << cu.error << ")\n";
    std::cerr << "\nFATAL: CUDA is mandatory and the runtime is not usable. "
                 "Run with `--gpus all` on a CUDA host.\n";
    return 2;
  }

  std::cout << "cuda devices  : " << cu.device_count << "\n";
  if (cu.device_count == 0) {
    std::cerr << "\nFATAL: no CUDA device visible. pfsolver has no CPU "
                 "fallback by design. Pass `--gpus all` to docker run.\n";
    return 2;
  }

  std::cout << "device 0      : " << cu.device_name << "  ("
            << human_bytes(cu.device_free_bytes) << " free / "
            << human_bytes(cu.device_total_bytes) << " total)\n";
  std::cout << "\nOK: CUDA-mandatory contract satisfied.\n";
  return 0;
}

int cmd_inspect(int argc, char** argv) {
  bool json = false;
  std::string bundle;
  for (int i = 2; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--json") {
      json = true;
    } else if (bundle.empty()) {
      bundle = arg;
    } else {
      pf::fail("inspect received unexpected extra argument: " + arg);
    }
  }
  if (bundle.empty()) {
    pf::fail("inspect requires <bundle_dir>");
  }
  const pf::Scene scene = pf::load_scene_bundle(bundle);
  if (json) {
    std::cout << pf::scene_to_json(scene).dump(2) << "\n";
  } else {
    pf::print_scene_summary(scene);
  }
  return 0;
}

void usage(std::ostream& os) {
  os << "usage: pfsolver <command>\n"
        "  version   print version\n"
        "  doctor    check toolchain + CUDA device (CUDA mandatory)\n"
        "  inspect   parse an SSW STEP bundle; pass --json for machine output\n";
}

} // namespace

int main(int argc, char** argv) {
  try {
    if (argc < 2) {
      usage(std::cerr);
      return 1;
    }
    const char* cmd = argv[1];
    if (std::strcmp(cmd, "version") == 0) return cmd_version();
    if (std::strcmp(cmd, "doctor") == 0) return cmd_doctor();
    if (std::strcmp(cmd, "inspect") == 0) return cmd_inspect(argc, argv);
    if (std::strcmp(cmd, "-h") == 0 || std::strcmp(cmd, "--help") == 0) {
      usage(std::cout);
      return 0;
    }

    std::cerr << "unknown command: " << cmd << "\n";
    usage(std::cerr);
    return 1;
  } catch (const pf::PfError& exc) {
    std::cerr << "FATAL: " << exc.what() << "\n";
    return 2;
  } catch (const std::exception& exc) {
    std::cerr << "FATAL: unexpected error: " << exc.what() << "\n";
    return 2;
  }
}
