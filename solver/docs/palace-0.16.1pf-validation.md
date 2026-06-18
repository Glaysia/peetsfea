# Palace 0.16.1pf validation package

Date: 2026-06-18.

## Build identity

- Top-level commit: `0a6062f875f025a9a758762df6b7425aa251bc29`.
- Palace submodule commit: `bc8c335b164ce6c7a2542ade6ee65968e68e4816`.
- Image tags: `peetsfea-palace:dev`, `peetsfea-palace:0.16.1pf`.
- Image ID: `sha256:0b1b1e027bb72f682106cd6fac9332e6694ef7f346628396e79fae664403b647`.
- Build info inside image:
  - `base_version=0.16.1`
  - `base_commit=c13e409f255392b9d78369c386276cf9343c2205`
  - `fork_version=0.16.1pf`
  - `source_commit=bc8c335b164ce6c7a2542ade6ee65968e68e4816`
  - `cuda_arch=86`
  - `palace_with_cuda=ON`

Build command:

```bash
cd solver
./docker/build.sh
```

Runtime smoke checks passed:

- `./docker/shell.sh cat /opt/peetsfea-palace/PEETSFEA_BUILD_INFO`
- `./docker/shell.sh palace -h`
- Docker config has `Entrypoint=null`, `Cmd=["/bin/bash","-l"]`.

## Schema and guard checks

Passed:

```bash
cd run/palace/goal2/schema-smoke
palace -serial -dry-run static_magnetic_loss.jsonc
```

Passed:

```bash
cd run/palace/goal2/ferrite-cpw
palace -serial -dry-run ferrite_table.jsonc
```

Expected fail-fast:

```bash
cd run/palace/goal2/schema-smoke
palace -serial -dry-run frequency_table.jsonc
```

The expected error is:

```text
Frequency-dependent material tables are not supported with WavePort boundaries; use LumpedPort/Terminal-style driven simulations.
```

## No-ferrite M1 regression

Final regression directory:
`run/palace/goal2/regression-final-bc8c335b/`.

Commands were run with the final `0.16.1pf` image, GPU enabled, and default
HYPRE pool override:

```text
device=134217728 unified=134217728 pinned=33554432 status=(0,0,0)
```

Compared against `run/palace/goal2/baseline-m1/`:

| File | max_abs | max_rel_scaled |
| --- | ---: | ---: |
| `cylinder_port-S.csv` | `1.000e-11` | `4.170e-12` |
| `cpw_port-S.csv` | `2.500e-10` | `5.742e-12` |
| `cpw_port-V.csv` | `3.000e-14` | `3.000e-14` |
| `cpw_port-I.csv` | `5.300e-16` | `5.300e-16` |

This confirms the fork preserves upstream-equivalent no-ferrite behavior within
GPU floating-point noise.

## Ferrite static magnetic loss

Small ferrite cylinder at 6.78 MHz:

- Configs: `run/palace/goal2/ferrite-cylinder/ferrite_real.jsonc`,
  `run/palace/goal2/ferrite-cylinder/ferrite_loss.jsonc`.
- Logs: `ferrite_real_final.log`, `ferrite_loss_final.log`.
- Both runs completed on GPU with default 128/128/32 MiB pools.

`port-S.csv` delta, real `mu=135.59` vs `MagneticLossTan=0.00218`:

```text
|S11| delta = -9.550592224609999e-09 dB
arg(S11) delta = -1.199992993861088e-09 deg
```

Terminal-style CPW ferrite at 6.78 MHz:

- Configs: `run/palace/goal2/ferrite-cpw/ferrite_real.jsonc`,
  `run/palace/goal2/ferrite-cpw/ferrite_loss.jsonc`.
- Logs: `ferrite_real_final_lowpool.log`, `ferrite_loss_final_lowpool.log`.
- Runs used explicit low pools due current GPU memory pressure:
  `device=16777216 unified=16777216 pinned=8388608`.
- Both runs completed on GPU with `LumpedPort` excitation.

`port-S.csv` delta, real `mu=135.59` vs `MagneticLossTan=0.00218`:

```text
max_abs = 6.779040899971278e-04
where = row 1, column 14
```

S-to-Z for the terminal ports also moves in the expected loss direction:

```text
real mu:        Re(Z11)=5.669538727850e-01, Re(Z22)=5.669538049718e-01
magnetic loss:  Re(Z11)=5.669545833539e-01, Re(Z22)=5.669545267242e-01
```

The magnetic loss term changes terminal-network S-parameters and increases the
terminal resistance terms, so the imaginary permeability term is active in the
Driven solve.

## Frequency-dependent material solve

Terminal-style CPW `PermeabilityFreq` single-point table:

- Config: `run/palace/goal2/ferrite-cpw/ferrite_table.jsonc`.
- Log: `run/palace/goal2/ferrite-cpw/ferrite_table_final_lowpool.log`.
- Run completed on GPU with `LumpedPort` excitation and low HYPRE pools.

Compared against the equivalent static `MagneticLossTan` run:

| File | max_abs | max_rel_scaled |
| --- | ---: | ---: |
| `port-S.csv` | `1.095e-08` | `1.221e-10` |
| `port-V.csv` | `1.000e-14` | `1.000e-14` |
| `port-I.csv` | `3.000e-16` | `3.000e-16` |

This confirms `PermeabilityFreq` is applied in the Driven solve loop and agrees
with the equivalent static magnetic loss at the same frequency.

## Remaining caveat

Frequency-dependent material tables are deliberately blocked for `WavePort`
configs. Use `LumpedPort` / terminal-network configs for GOAL1 ferrite emission.
