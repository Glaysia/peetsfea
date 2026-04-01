# Non-Sampling Fallback Audit

## Scope And Exclusions

This audit inventories fallback patterns outside TOML sampling feasibility search. It was gathered via parallel passes over geometry/AEDT runtime code, orchestration/pipeline code, and tests/docs.

- Excluded:
  - `src/peetsfea/spec/resolver/*`
  - `src/peetsfea/pipeline/selection/*`
  - retry/attempt-driven TOML feasibility search
  - manifest retry fields that exist to preserve that sampling contract
- Included:
  - runtime fallback behavior that converts a real failure or missing expected state into substitute success, degraded output, compatibility continuation, skipped required work, or silent suppression
  - fallback-shaped helper signatures and dead utilities that still keep fallback semantics alive in the codebase
  - tests/docs that encode those non-sampling fallback expectations

## Active Runtime Fallbacks

| Severity | Area | File | Symbol | Current Behavior | Why It Is A Fallback | Removal Direction |
| --- | --- | --- | --- | --- | --- | --- |
| High | Geometry finalize | `src/peetsfea/backend/pyaedt/geometry/builders/build_finalize_ops.py` | `_finalize_solids_and_substrates_impl()` | After creating the `tx_vertical` bridge, the code intentionally `continue`s instead of uniting the new bridge into the live conductors. The comment explicitly says this is a diagnostic bypass so the build can continue with separated conductors. | A failing or incomplete unite path is converted into a successful build with degraded conductor state. | Remove the bypass and require the expected unite step to succeed or raise immediately. |
| Medium | Geometry naming | `src/peetsfea/backend/pyaedt/geometry/rules/solid_ops.py` | `normalize_united_name()`, `safe_unite()` | If `modeler.unite()` returns an empty list, `normalize_united_name()` substitutes `fallback_name` and treats the unite as successful. Representative callers include bridge, terminal, FR4, TX bridge, finalize, and via builders. | Missing unite output is converted into a substitute object name instead of being treated as a failure. | Require a non-empty named result from unite; raise on empty lists or unnamed objects. |
| Medium | Geometry via closure | `src/peetsfea/backend/pyaedt/geometry/builders/build_via_ops.py` | `_tx_dd_xy_tools()` | Falls back from explicit per-layer TX-DD object maps to `group_objects["tx_dd"]`, then returns `[]` if all names are dead. | Required live subtraction tools are downgraded into broader guesses and then into an empty-success result. | Require explicit live layer-owned objects for the caller and raise when the tool set is empty or unresolved. |
| Medium | Geometry FR4 subtract | `src/peetsfea/backend/pyaedt/geometry/builders/build_fr4_ops.py` | `_finalize_fr4_and_save_project()` | Uses `_tx_dd_xy_tools()` for TX tools and silently skips subtraction when `fr4_tools` is empty for non-`tx/XY` cases. | Required copper subtraction can be skipped while the build still succeeds. | Tighten FR4 subtraction preconditions so missing live tools raise instead of continuing. |
| Low | Geometry via closure | `src/peetsfea/backend/pyaedt/geometry/builders/build_via_ops.py` | `_close_stacked_tx_dd_half_conductors_with_hex_vias()` | Returns `preferred_object_name` unchanged when layer-object or unique-name closure preconditions are missing. | A helper whose job is to close stacked conductors preserves prior ownership and lets finalize keep going. | Replace passthrough returns with invariant checks that raise when stacked closure inputs are incomplete. |
| Medium | Geometry live-name inference | `src/peetsfea/backend/pyaedt/geometry/builders/build_finalize_ops.py` | `_resolve_live_tx_vertical_object_name()` | If the preferred name is gone, the helper infers substitutes by `right`/`left` suffix heuristics or by accepting the sole remaining live object. | Missing expected object identity is converted into heuristic substitution. | Remove heuristic matching and require the exact expected live object name. |
| Medium | Orchestration | `entry/build.py` | `build_entries()`, `build_all_targets_with_options()` | `stop_on_error=False` preserves a best-effort branch, and missing manifests are printed as `skip missing manifest=...` and skipped instead of failing immediately. | Required build inputs and failures are converted into continuation semantics. | Reject `stop_on_error=False` and make missing manifest inputs fail immediately. |
| Medium | Pipeline cleanup | `src/peetsfea/pipeline/run_batch.py` | `_safe_remove()`, `_cleanup_failed_design_files()`, `cleanup_aedtresults()` | Uses `shutil.rmtree(..., ignore_errors=True)` and `unlink(missing_ok=True)` so cleanup failures are silently suppressed. | Cleanup errors can leave stale artifacts or locks while the pipeline keeps moving. | Raise on cleanup failures except for genuinely absent optional targets proven irrelevant to correctness. |
| Low | Replay export | `src/peetsfea/pipeline/run_batch.py` | `_canonicalize_resolved_pcbs()` | If a PCB exists in the resolved spec but not in `selected_pcbs`, the function `continue`s and leaves the entry uncanonicalized. | Internal replay/export invariant break is treated as tolerable drift. | Require every resolved-spec PCB to match selected state or raise with PCB identity context. |
| Low | Compatibility surface | `src/peetsfea/pipeline/run_batch.py`, `entry/build.py` | `build_aedt_from_manifest_entry_with_options()`, `_build_entry()` | `raise_on_error` and `bool` success returns are still threaded through the interface even though the implementation already re-raises on real failure. | The API shape still advertises best-effort compatibility despite fail-fast runtime behavior. | Remove stale compatibility parameters and return contracts so the surface matches actual fail-fast semantics. |

## Signature / Dead-Surface Fallbacks

| Kind | File | Symbol | Current Surface | Why It Still Matters | Retirement Direction |
| --- | --- | --- | --- | --- | --- |
| Signature baggage | `src/peetsfea/aedt/proxies.py` | `object_name(..., fallback=...)` | Carries a fallback parameter although the implementation already requires and returns the real object name. | The signature keeps fallback semantics visible to callers and tests. | Remove the fallback parameter and require exact-name resolution. |
| Signature baggage | `src/peetsfea/aedt/proxies.py` | `set_object_model_state(..., fallback_name=...)` | Threads `fallback_name` through model-state updates even though object-name lookup is strict. | The API shape still implies substitute naming is acceptable. | Remove `fallback_name` and require the real object identity. |
| Signature baggage | `src/peetsfea/aedt/proxies.py` | `unite(..., fallback_name=...)` | Keeps fallback naming in the helper contract even though the proxy-side normalizer already asserts non-empty results. | This keeps geometry callers written around fallback-name semantics. | Collapse to a strict unite contract with no fallback parameter. |
| Signature baggage | `src/peetsfea/backend/pyaedt/geometry/rules/cad_probe.py` | `_probe_cad_object(..., fallback_name)`, `_object_name(..., fallback)` | Both carry fallback parameters, but the fallback value is ignored and a real object name is still required. | Dead fallback arguments make the call sites look like fallback behavior is supported. | Remove the unused fallback parameters. |
| Dead utility | `src/peetsfea/backend/pyaedt/em_pipeline/steps/excitation_names.py` | `select_regex_fallback_name()` | Regex/name fallback utility remains defined, but the active runtime source path now requires exact names. | A dead fallback helper keeps the old behavior discoverable and tests still target it. | Delete the helper or rewrite tests/docs to reflect exact-name fail-fast behavior. |

## Tests And Docs Encoding Fallback Behavior

| Kind | File | Encodes | Matches Live Runtime? | Update Need |
| --- | --- | --- | --- | --- |
| Doc | `docs/type2-reuse.md` | Documents `fallback_name` as an accepted reuse pattern for CAD probing and `safe_unite()`. | Yes for `solid_ops.py`; no for stricter proxy-side helpers. | Update when fallback-name contracts are removed. |
| Test | `tests/backend_geometry_rules/test_tx_dd_left_a_to_vertical_bridge_points.py` | `_tx_dd_xy_tools()` fallback from layer maps to `group_objects["tx_dd"]` and empty-result behavior when all fallback names are dead. | Yes. | Update alongside `_tx_dd_xy_tools()` removal or tightening. |
| Test | `tests/backend_geometry_build/test_one_turn_geometry_build.py` | Diagnostic bypass around the missing unite call for the `tx_vertical` bridge and helper-level `fallback_name` usage. | Yes. | Update when finalize no longer allows separated-conductor success. |
| Test | `tests/backend_em/test_aedt_sidecar.py` | Fallback-shaped proxy/helper signatures such as `fallback_name` on unite, object-name, and model-state helpers. | Partially; runtime is stricter than the exposed signatures. | Update when signature baggage is retired. |
| Test | `tests/backend_em/test_em_pipeline_sources.py` | RX stub excitation fallback expectations, including canonical stub preference over alternate matches. | No; runtime source resolution is already exact-name fail-fast. | Mark as drift and rewrite to assert failure semantics. |
| Test | `tests/backend_em/test_em_pipeline.py` | Default/preferred terminal-name fallback behavior in EM pipeline expectations. | Partially; some default naming still exists, but regex-style fallback expectations have drifted. | Split preserved default naming from dead fallback expectations and update accordingly. |
| Test | `tests/pipeline_runs/test_manifest_validation.py` | Acceptance/ignore of legacy `trace_gap_profile` while the new geometry section remains authoritative. | Yes. | Decide whether legacy acceptance is intentional compatibility or a fallback to remove later; document that decision when implementation changes. |
| Test | `tests/pipeline_runs/test_run_script_artifacts.py` | `stop_on_error` / `raise_on_error` compatibility assumptions, including current skip-missing-manifest behavior. | Yes. | Update when orchestration surfaces are made strictly fail-fast. |

## Not In Scope

- Sampling retry/attempt behavior in `selection/*`.
- Determinism tests and manifest retry metadata tied to TOML feasibility search.
- Ordinary loop `continue` statements that do not suppress required failures.
- Mode guards that are normal feature gating rather than degraded success, including:
  - ferrite-disabled `return [], [], []` in `scene_objects.py`
  - non-applicable ranking maps such as `return {}` in `placement_rules.py`
- Fail-fast proxy/wrapper paths that already re-raise instead of degrading, even if some call sites still carry fallback-shaped signatures.
