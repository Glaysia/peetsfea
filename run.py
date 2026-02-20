from peetsfea import RunConfig, run


DEFAULT_RUN_CONFIG = {
    "ansys_executable_path": "/opt/ansys_inc/v252/AnsysEM",
    "ansys_run_dir": "/home/harry/Projects/PythonProjects/peetsfea/run",
    "toml_path": "/home/harry/Projects/PythonProjects/peetsfea/run/type1.toml",
    "seed": 1,
    "backend": "hfss",
}
if __name__ == "__main__":
    print(run(RunConfig(**DEFAULT_RUN_CONFIG))["design_id"])
