# Palace 0.16.1pf material contract

Purpose: this is the GOAL1 emitter contract for the forked Palace engine.
`0.16.1pf` means stock Palace `0.16.1` plus the peetsfea ferrite material
extension. The CLI contract stays unchanged: JSON config in, Palace CSV outputs
out.

## Runtime boundary

- Image tag: `peetsfea-palace:0.16.1pf`.
- Palace fork commit: `bc8c335b164ce6c7a2542ade6ee65968e68e4816`.
- Supported problem type for the new fields: `Problem.Type = "Driven"` only.
- Supported port style for frequency-dependent material tables:
  `LumpedPort` / terminal-style driven simulations.
- `WavePort` plus frequency-dependent material tables is intentionally rejected.
  The wave-port mode solve still uses static material data, so accepting this
  combination would produce a misleading solve.

## Static magnetic loss

Use existing `Permeability` for real relative permeability `mu'`. Add exactly
one of `MagneticLossTan` or `PermeabilityImag` for magnetic loss:

```jsonc
{
  "Attributes": [2],
  "Permeability": 135.59,
  "MagneticLossTan": 0.00218,
  "Permittivity": [9.3, 9.3, 11.5],
  "LossTan": [3.0e-5, 3.0e-5, 8.6e-5]
}
```

Equivalent explicit imaginary permeability:

```jsonc
{
  "Attributes": [2],
  "Permeability": 135.59,
  "PermeabilityImag": 0.2955862
}
```

Interpretation:

- Palace uses `mu = mu' - j mu''`.
- `MagneticLossTan = mu'' / mu'`.
- `PermeabilityImag` is `mu''`, not the signed complex value.
- Values may be scalar or length-3 principal-axis arrays. Existing
  `MaterialAxes` applies to both real and imaginary principal values.
- `LossTan` remains the dielectric/electric loss tangent for permittivity.

Parser constraints:

- `Permeability` must be positive.
- `MagneticLossTan` and `PermeabilityImag` are non-negative.
- Do not specify both `MagneticLossTan` and `PermeabilityImag`.

## Frequency-dependent tables

Use `PermeabilityFreq` for scalar dispersive permeability and
`PermittivityFreq` for scalar dispersive permittivity:

```jsonc
{
  "Attributes": [2],
  "Permeability": 135.59,
  "PermeabilityFreq": {
    "Freq": [0.00678],
    "Real": [135.59],
    "LossTan": [0.00218]
  }
}
```

Table fields:

- `Freq`: required, GHz in the config, positive and strictly increasing.
- `Real`: required, positive.
- `Imag`: optional non-negative imaginary part.
- `LossTan`: optional non-negative loss tangent.
- Use at most one of `Imag` or `LossTan`.

Evaluation:

- A single-point table only accepts the matching solve frequency.
- Multi-point tables use linear interpolation inside the table range.
- Solving outside the table range is fail-fast.
- The frequency-dependent contribution is applied inside the Driven frequency
  loop, so frequency sweeps see the interpolated material at each sample.

## GOAL1 emitter guidance

- For no-ferrite runs, keep emitting stock Palace material fields only.
- For ferrite terminal-network runs, set `PFSOLVER_PALACE_IMAGE` to
  `peetsfea-palace:0.16.1pf` and emit `PermeabilityFreq` from
  `solver/data/materials.toml` using GHz frequencies.
- Prefer `LossTan` in the table when the material source has `mu'` plus
  magnetic loss tangent. Use `Imag` only when the source gives `mu''` directly.
- Do not emit frequency-dependent material tables for `WavePort` configs.
- The CSV output contract is unchanged: `postpro/port-S.csv`,
  `postpro/port-V.csv`, and `postpro/port-I.csv`.

