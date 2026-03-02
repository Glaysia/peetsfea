#!/usr/bin/env bash

set -u

usage() {
  cat <<'EOF'
Usage:
  ./multiple.bash --process <count> --chunk-size <count> [--start-seed <seed>]

Example:
  ./multiple.bash --process 4 --chunk-size 25
  # worker 0: seed 0-24
  # worker 1: seed 25-49
  # worker 2: seed 50-74
  # worker 3: seed 75-99

  ./multiple.bash --process 4 --chunk-size 25 --start-seed 10001
  # worker 0: seed 10001-10025
  # worker 1: seed 10026-10050
  # worker 2: seed 10051-10075
  # worker 3: seed 10076-10100
EOF
}

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

is_non_negative_int() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

process_count=""
chunk_size=""
start_seed="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --process)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --process" >&2
        usage
        exit 1
      fi
      process_count="$2"
      shift 2
      ;;
    --chunk-size)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --chunk-size" >&2
        usage
        exit 1
      fi
      chunk_size="$2"
      shift 2
      ;;
    --start-seed)
      if [[ $# -lt 2 ]]; then
        echo "Missing value for --start-seed" >&2
        usage
        exit 1
      fi
      start_seed="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$process_count" || -z "$chunk_size" ]]; then
  echo "Both --process and --chunk-size are required." >&2
  usage
  exit 1
fi

if ! is_positive_int "$process_count"; then
  echo "--process must be a positive integer: $process_count" >&2
  exit 1
fi

if ! is_positive_int "$chunk_size"; then
  echo "--chunk-size must be a positive integer: $chunk_size" >&2
  exit 1
fi

if ! is_non_negative_int "$start_seed"; then
  echo "--start-seed must be a non-negative integer: $start_seed" >&2
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_bin="$script_dir/../.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  python_bin="python"
fi

(cd "$script_dir" && rm -rf ./aedt/*)

declare -a pids=()
declare -a labels=()

for ((worker=0; worker<process_count; worker++)); do
  worker_start_seed=$((start_seed + (worker * chunk_size)))
  worker_end_seed=$((worker_start_seed + chunk_size - 1))
  label="worker-${worker}:${worker_start_seed}-${worker_end_seed}"
  labels+=("$label")
  (
    for ((seed=worker_start_seed; seed<=worker_end_seed; seed++)); do
      echo "[$label] seed=$seed"
      "$python_bin" "$script_dir/../run.py" "$seed"
    done
  ) &
  pids+=("$!")
done

failed=0
for i in "${!pids[@]}"; do
  pid="${pids[$i]}"
  label="${labels[$i]}"
  if ! wait "$pid"; then
    echo "[$label] failed" >&2
    failed=1
  fi
done

if [[ "$failed" -ne 0 ]]; then
  exit 1
fi

echo "All workers completed successfully."
