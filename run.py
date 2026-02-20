from peetsfea import RunConfig, build_square_spiral_from_manifest, run

DEFAULT_RUN_CONFIG = {
    "ansys_executable_path": "/opt/ansys_inc/v252/AnsysEM",
    "ansys_run_dir": "/home/harry/Projects/PythonProjects/peetsfea/run/aedt",
    "toml_path": "/home/harry/Projects/PythonProjects/peetsfea/run/type1.toml",
    "seed": 1,
    "backend": "hfss",
    "non_graphical": False,
    "close_on_exit": False,
}
if __name__ == "__main__":
    config = RunConfig(**DEFAULT_RUN_CONFIG)
    manifest = run(config)
    geometry = build_square_spiral_from_manifest(manifest)
    print(geometry["aedt_path"])
