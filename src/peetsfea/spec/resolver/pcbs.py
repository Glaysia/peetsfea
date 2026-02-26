from __future__ import annotations

import warnings
from typing import Literal, cast

from peetsfea.spec.loader import TOMLTable, TOMLValue
from peetsfea.types.manifest import ResolvedPcbInstance, ResolvedPcbMount

from .constants import FIXED_PCB_ORDER, FIXED_PCB_RULES, GROUP_KIND_ORDER, PCB_OFFSET_BASE, PCB_SPACING_OFFSET_BASE
from .sampling import build_candidates, sample_candidate, select_range_value
from .types import PcbMountSpec, SamplingContext


def parse_position(value: TOMLValue, name: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name} must be [x, y, z]")
    out: list[float] = []
    for idx, entry in enumerate(value):
        if isinstance(entry, bool) or not isinstance(entry, (int, float)):
            raise ValueError(f"{name}[{idx}] must be number")
        out.append(float(entry))
    return (out[0], out[1], out[2])


def parse_pcb_mounts(value: TOMLValue, name: str) -> list[ResolvedPcbMount]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    mounts: list[ResolvedPcbMount] = []
    for idx, entry in enumerate(value):
        if not isinstance(entry, dict):
            raise ValueError(f"{name}[{idx}] must be a table/object")
        if set(entry.keys()) - {"kind", "selector_mode", "selector_index"}:
            raise ValueError(f"{name}[{idx}] contains unsupported keys")
        kind_raw = entry.get("kind")
        if kind_raw not in GROUP_KIND_ORDER:
            raise ValueError(f"{name}[{idx}].kind must be one of {list(GROUP_KIND_ORDER)}")
        selector_mode_raw = entry.get("selector_mode")
        if selector_mode_raw not in ("all", "index"):
            raise ValueError(f"{name}[{idx}].selector_mode must be 'all' or 'index'")
        selector_mode = cast(Literal["all", "index"], selector_mode_raw)
        selector_index_raw = entry.get("selector_index")
        selector_index: int | None
        if selector_mode == "all":
            if selector_index_raw is not None:
                raise ValueError(f"{name}[{idx}].selector_index must be omitted when selector_mode='all'")
            selector_index = None
        else:
            if isinstance(selector_index_raw, bool) or not isinstance(selector_index_raw, int):
                raise ValueError(f"{name}[{idx}].selector_index must be int when selector_mode='index'")
            if selector_index_raw < 0:
                raise ValueError(f"{name}[{idx}].selector_index must be >= 0")
            selector_index = selector_index_raw
        mounts.append(
            {
                "kind": cast(Literal["tx_dd", "tx_vertical", "rx_dd"], kind_raw),
                "selector_mode": selector_mode,
                "selector_index": selector_index,
            }
        )
    return mounts


def resolve_pcbs(spec: TOMLTable, seed: int, attempt: int, context: SamplingContext) -> list[ResolvedPcbInstance]:
    raw_pcbs = spec.get("pcbs")
    if not isinstance(raw_pcbs, list) or len(raw_pcbs) == 0:
        raise ValueError("pcbs must be a non-empty array of tables")

    resolved: list[ResolvedPcbInstance] = []
    ids: set[str] = set()
    for idx, raw_pcb in enumerate(raw_pcbs):
        if not isinstance(raw_pcb, dict):
            raise ValueError(f"pcbs[{idx}] must be a table/object")
        raw_pcb_table = raw_pcb
        raw_id = raw_pcb_table.get("id")
        raw_role = raw_pcb_table.get("role")
        if not isinstance(raw_id, str) or not raw_id:
            raise ValueError(f"pcbs[{idx}].id must be non-empty string")
        if raw_id in ids:
            raise ValueError(f"Duplicate pcb id: {raw_id}")
        ids.add(raw_id)
        if raw_role not in ("tx", "rx"):
            raise ValueError(f"pcbs[{idx}].role must be 'tx' or 'rx'")
        role = cast(Literal["tx", "rx"], raw_role)

        raw_position = raw_pcb_table.get("position")
        if raw_position is None:
            raise ValueError(f"pcbs[{idx}].position must be [x, y, z]")
        position = parse_position(raw_position, f"pcbs[{idx}].position")
        raw_rotation = raw_pcb_table.get("rotation_deg")
        if isinstance(raw_rotation, bool) or not isinstance(raw_rotation, (int, float)):
            raise ValueError(f"pcbs[{idx}].rotation_deg must be number")
        raw_mounts = raw_pcb_table.get("mounts")
        if raw_mounts is None:
            raise ValueError(f"pcbs[{idx}].mounts must be a list")
        mounts = parse_pcb_mounts(raw_mounts, f"pcbs[{idx}].mounts")
        raw_present = raw_pcb_table.get("present")
        if not isinstance(raw_present, list) or len(raw_present) != 4:
            raise ValueError(f"pcbs[{idx}].present must be [is_integer, start, end, count]")
        is_integer, start, end, count = raw_present
        if is_integer is not True:
            raise ValueError(f"pcbs[{idx}].present[0] (is_integer) must be true")
        if any(isinstance(v, bool) for v in (start, end, count)):
            raise ValueError(f"pcbs[{idx}].present values must be numeric")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or not isinstance(count, int):
            raise ValueError(f"pcbs[{idx}].present must be [is_integer, start, end, count]")
        candidates = build_candidates(True, float(start), float(end), count)
        if not all(int(v) in (0, 1) for v in candidates):
            raise ValueError(f"pcbs[{idx}].present candidates must be 0 or 1")
        present_key = f"pcbs[{idx}].present"
        if present_key in context:
            present = bool(int(context[present_key]))
        else:
            present = bool(int(sample_candidate(candidates, seed=seed, offset=PCB_OFFSET_BASE + idx, attempt=attempt)))
            context[present_key] = int(present)

        raw_z_mode = raw_pcb_table.get("z_mode")
        if raw_z_mode not in ("absolute", "relative_to_pcb"):
            raise ValueError(f"pcbs[{idx}].z_mode must be 'absolute' or 'relative_to_pcb'")
        z_mode = cast(Literal["absolute", "relative_to_pcb"], raw_z_mode)
        raw_z_relative_base_id = raw_pcb_table.get("z_relative_base_id")
        raw_z_delta_path = raw_pcb_table.get("z_delta_path")
        z_relative_base_id: str | None = None
        z_delta_path: str | None = None
        if z_mode == "absolute":
            if raw_z_relative_base_id is not None or raw_z_delta_path is not None:
                raise ValueError(
                    f"pcbs[{idx}] absolute z_mode must not set z_relative_base_id or z_delta_path"
                )
        else:
            if not isinstance(raw_z_relative_base_id, str) or raw_z_relative_base_id == "":
                raise ValueError(f"pcbs[{idx}].z_relative_base_id must be non-empty string when z_mode='relative_to_pcb'")
            if not isinstance(raw_z_delta_path, str) or raw_z_delta_path == "":
                raise ValueError(f"pcbs[{idx}].z_delta_path must be non-empty string when z_mode='relative_to_pcb'")
            z_relative_base_id = raw_z_relative_base_id
            z_delta_path = raw_z_delta_path

        resolved.append(
            {
                "id": raw_id,
                "role": role,
                "position": position,
                "rotation_deg": float(raw_rotation),
                "present": present,
                "z_mode": z_mode,
                "z_relative_base_id": z_relative_base_id,
                "z_delta_path": z_delta_path,
                "mounts": mounts,
            }
        )

    by_id: dict[str, ResolvedPcbInstance] = {resolved_pcb["id"]: resolved_pcb for resolved_pcb in resolved}
    for idx, resolved_pcb in enumerate(resolved):
        if resolved_pcb["z_mode"] != "relative_to_pcb":
            continue
        base_id = resolved_pcb["z_relative_base_id"]
        delta_path = resolved_pcb["z_delta_path"]
        if base_id is None or delta_path is None:
            raise ValueError(
                f"pcbs[{idx}] relative_to_pcb requires z_relative_base_id and z_delta_path"
            )
        base = by_id.get(base_id)
        if base is None:
            raise ValueError(f"pcbs[{idx}].z_relative_base_id references unknown pcb id: {base_id}")
        if base["z_mode"] != "absolute":
            raise ValueError(f"pcbs[{idx}].z_relative_base_id must reference an absolute-z pcb (actual={base_id})")
        delta = float(
            select_range_value(
                spec,
                delta_path,
                expect_integer=False,
                seed=seed,
                offset=PCB_SPACING_OFFSET_BASE + idx,
                attempt=attempt,
                context=context,
            )
        )
        x, y, _ = resolved_pcb["position"]
        resolved_pcb["position"] = (x, y, base["position"][2] + delta)
    return resolved


def mount_specs(mounts: list[ResolvedPcbMount]) -> tuple[PcbMountSpec, ...]:
    return tuple((mount["kind"], mount["selector_mode"], mount["selector_index"]) for mount in mounts)


def mounts_from_specs(specs: tuple[PcbMountSpec, ...]) -> list[ResolvedPcbMount]:
    out: list[ResolvedPcbMount] = []
    for kind, selector_mode, selector_index in specs:
        out.append({"kind": kind, "selector_mode": selector_mode, "selector_index": selector_index})
    return out


def normalize_pcbs_fixed_topology(pcbs: list[ResolvedPcbInstance]) -> list[ResolvedPcbInstance]:
    by_id: dict[str, ResolvedPcbInstance] = {pcb["id"]: pcb for pcb in pcbs}
    missing = [pcb_id for pcb_id in FIXED_PCB_ORDER if pcb_id not in by_id]
    extra = sorted(pcb_id for pcb_id in by_id.keys() if pcb_id not in FIXED_PCB_RULES)
    if missing or extra:
        detail_parts: list[str] = []
        if missing:
            detail_parts.append(f"missing={missing}")
        if extra:
            detail_parts.append(f"extra={extra}")
        detail = ", ".join(detail_parts)
        raise ValueError(
            "spec_version 0.2.6 requires fixed pcbs topology ids "
            f"{list(FIXED_PCB_ORDER)} ({detail})"
        )

    normalized: list[ResolvedPcbInstance] = []
    for pcb_id in FIXED_PCB_ORDER:
        pcb = by_id[pcb_id]
        rule = FIXED_PCB_RULES[pcb_id]
        if pcb["role"] != rule["role"]:
            raise ValueError(
                "spec_version 0.2.6 fixed topology requires "
                f"pcbs.{pcb_id}.role='{rule['role']}' (actual={pcb['role']})"
            )

        expected_present = rule["present"]
        if pcb["present"] != expected_present:
            warnings.warn(
                f"pcbs.{pcb_id}.present normalized to {expected_present} for spec_version 0.2.6 fixed topology",
                UserWarning,
                stacklevel=2,
            )
            pcb["present"] = expected_present

        expected_mounts = rule["mounts"]
        if mount_specs(pcb["mounts"]) != expected_mounts:
            warnings.warn(
                f"pcbs.{pcb_id}.mounts normalized to fixed topology mapping for spec_version 0.2.6",
                UserWarning,
                stacklevel=2,
            )
            pcb["mounts"] = mounts_from_specs(expected_mounts)
        normalized.append(pcb)
    return normalized
