from __future__ import annotations

import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

from run import run_one

MAX_WORKERS = 6
TOTAL_SEEDS = 10000


def _run_seed(seed: int) -> tuple[int, bool]:
    return seed, run_one(seed)


def run_many() -> None:
    failed_seeds: list[int] = []

    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_run_seed, seed) for seed in range(TOTAL_SEEDS)]
        for future in as_completed(futures):
            seed, ok = future.result()
            if not ok:
                failed_seeds.append(seed)

    failed_seeds.sort()
    if failed_seeds:
        print(f"failed seeds: {failed_seeds}")
    else:
        print("all seeds completed successfully")


def main() -> None:
    cli_seed: int | None = None
    if len(sys.argv) > 1:
        try:
            cli_seed = int(sys.argv[1])
        except ValueError as exc:
            raise SystemExit(f"Invalid seed '{sys.argv[1]}'. Usage: python run_with_process.py [seed]") from exc

    if cli_seed is not None:
        run_one(cli_seed)
        return

    run_many()


if __name__ == "__main__":
    main()
