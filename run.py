from peetsfea import RunConfig, build_square_spiral_from_manifest, run


def run_one(seed: int) -> None:
    config = RunConfig(
        ansys_executable_path="/opt/ansys_inc/v252/AnsysEM",
        ansys_run_dir="/home/harry/Projects/PythonProjects/peetsfea/run/aedt",
        toml_path="/home/harry/Projects/PythonProjects/peetsfea/run/type1.toml",
        seed=seed,
        backend="hfss",
        non_graphical=False,
        close_on_exit=False,
    )
    manifest = run(config)
    geometry = build_square_spiral_from_manifest(manifest)
    print(geometry["aedt_path"])

MANY = "MANY"
SINGLE = "SINGLE"


RUN_MODE = MANY
# RUN_MODE = SINGLE

if __name__ == "__main__":
    if RUN_MODE == MANY:
        for seed in range(95, 152):
            run_one(seed)
    elif RUN_MODE == SINGLE:
        run_one(2)
