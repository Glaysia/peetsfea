cmake_minimum_required(VERSION 3.22)
project(pfsolver LANGUAGES CXX VERSION 0.0.1)

# ---------------------------------------------------------------------------
# peetsfea CUDA C++ FEM solver — terminal-network (HFSS full-wave replacement)
#
# Design rule (see cpp-cuda-fem-solver-longterm-plan.html):
#   CUDA is MANDATORY. There is no CPU build and no CPU fallback. A toolchain
#   without the CUDA toolkit must fail to configure, not silently degrade.
# ---------------------------------------------------------------------------

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release CACHE STRING "" FORCE)
endif()

# CUDA-mandatory: REQUIRED means configuration aborts when no CUDA toolkit.
find_package(CUDAToolkit REQUIRED)

# 4-core MPI is part of the run contract; require it at build time too.
find_package(MPI REQUIRED)

add_executable(pfsolver
  src/main.cpp
  src/cuda_probe.cpp
  src/env_report.cpp
)
target_include_directories(pfsolver PRIVATE src)
target_link_libraries(pfsolver PRIVATE CUDA::cudart MPI::MPI_CXX)
target_compile_definitions(pfsolver PRIVATE
  PFSOLVER_VERSION="${PROJECT_VERSION}"
)

install(TARGETS pfsolver RUNTIME DESTINATION bin)
