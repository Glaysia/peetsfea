# syntax=docker/dockerfile:1
#
# pfsolver application image, built on the heavy Palace base.
# Iterating C++ here is cheap because the base (Palace/spack) is already built.
#
#   docker build -f docker/Dockerfile -t pfsolver:latest ..
#   docker run --rm --gpus all pfsolver:latest doctor
#
ARG BASE_IMAGE=peetsfea-solver-base:0.16.0
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-lc"]
WORKDIR /src
COPY CMakeLists.txt ./
COPY src ./src

# The spack env (cuda, mpi) is activated via /etc/profile.d by the login shell.
RUN cmake -S . -B /build -G Ninja -DCMAKE_BUILD_TYPE=Release \
 && cmake --build /build --parallel \
 && cmake --install /build --prefix /usr/local

ENTRYPOINT ["/bin/bash", "-lc", "exec pfsolver \"$@\"", "--"]
CMD ["doctor"]
