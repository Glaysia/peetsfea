# Local podman/docker-wrapped Palace (for pfsolver dev)

`pfsolver`는 Palace를 **로컬에서 컨테이너로 감싼 `palace` 바이너리**로 호출한다 —
pyaedt가 podman-wrapped ansysedt를 쓰는 것과 동일한 패턴.

## 지금 쓰는 버전 (중요)
- **stock 릴리스 `0.16.1`** (포크 패치 없음). 이미지 태그 `palace:0.16.1`.
- 포크가 개발하는 자기손실 패치 버전 = **`0.16.1pfs`** (이미지 `palace:0.16.1pfs`, GOAL2 산출). pfsolver는
  당장은 stock `0.16.1`을 쓰고, ferrite 단계에서 `PFSOLVER_PALACE_IMAGE=palace:0.16.1pfs`로 바꾼다.

## 설치
```bash
cd solver/local
./install-palace-local.sh wrapper   # ~/.local/bin/palace 설치 (즉시)
./install-palace-local.sh build     # palace:0.16.1 이미지 빌드 (heavy, 1회)
# 또는 all = build + wrapper
```
설치 후 `palace <config.json>`가 마치 로컬 바이너리처럼 동작(컨테이너에서 4-rank GPU 실행).

## pfsolver / Codex가 호출하는 법
pfsolver는 `palace`를 **런타임 무관 래퍼**로 부른다. 직접 `docker run`/`podman run`을 하드코딩하지 말 것.
- 기본: `~/.local/bin/palace <config.json>` (PATH에 `~/.local/bin`).
- 환경변수로 제어:
  - `PFSOLVER_CONTAINER_RUNTIME=podman|docker` (기본 podman, NVIDIA CDI `/etc/cdi/nvidia.yaml`)
  - `PFSOLVER_PALACE_IMAGE=palace:0.16.1` (포크 단계엔 `palace:0.16.1pfs`)
  - `PFSOLVER_MPI_RANKS=4`
  - `PFSOLVER_WORKDIR=$PWD` (config/mesh 경로가 컨테이너 안에서도 동일하게 보이도록 같은 경로로 마운트)
- 산출: 컨테이너가 `postpro/port-S.csv`·`port-V.csv`·`port-I.csv`를 `PFSOLVER_WORKDIR` 아래에 남김 → pfsolver가 읽어 Z 도출.

## CUDA mandatory
이미지는 CUDA-only. GPU 미부착 시 palace 실패(폴백 없음). pfsolver는 invoke 전 GPU 게이트.

## enroot (클러스터)
enroot은 **빌드 도구가 아니라 런타임**이다. 위 이미지를 docker/podman으로 빌드 → export →
`enroot import dockerd://palace:0.16.1`(또는 registry) → `.sqsh` → `enroot create/start`,
또는 Slurm pyxis `srun --container-image=palace:0.16.1 … mpirun -np 4 palace config.json`.
이 래퍼(`~/.local/bin/palace`)는 로컬 dev(podman/docker)용이고, 클러스터에선 enroot 경로를 쓴다 —
그래서 pfsolver의 palace 호출은 런타임 무관으로 추상화돼 있어야 한다.
