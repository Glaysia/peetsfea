from __future__ import annotations

from .build_common import *
from .build_port_ops import _points_close

def _dedupe_names(names: list[str]) -> list[str]:
    deduped: list[str] = []
    for name in names:
        if name not in deduped:
            deduped.append(name)
    return deduped

def _replace_group_object_name(
    *,
    group_objects: GroupObjects,
    group_key: Literal["tx_dd", "tx_vertical"],
    old_name: str,
    new_name: str,
    removed_name: str = "",
) -> None:
    updated: list[str] = []
    for name in group_objects[group_key]:
        if removed_name and name == removed_name:
            continue
        if name == old_name:
            updated.append(new_name)
        else:
            updated.append(name)
    group_objects[group_key] = _dedupe_names(updated)

def _replace_object_name_in_list(names: list[str], *, old_name: str, new_name: str, removed_name: str = "") -> None:
    updated: list[str] = []
    for name in names:
        if removed_name and name == removed_name:
            continue
        if name == old_name:
            updated.append(new_name)
        else:
            updated.append(name)
    names[:] = _dedupe_names(updated)

def _replace_object_name_in_landing(
    landing: _DirectedLandingSection,
    *,
    old_name: str,
    new_name: str,
) -> None:
    if not state_is_set(landing):
        return
    if landing["object_name"] == old_name:
        landing["object_name"] = new_name
    if "stub_face_ref" in landing and landing["stub_face_ref"]["object_name"] == old_name:
        landing["stub_face_ref"]["object_name"] = new_name

def _replace_object_name_in_tx_series_binding_inputs(
    binding: _TxSeriesBindingInputs | _TxSeriesChainBinding,
    *,
    old_name: str,
    new_name: str,
) -> None:
    if not state_is_set(binding):
        return
    if isinstance(binding, dict):
        _replace_object_name_in_landing(binding["feed_in"], old_name=old_name, new_name=new_name)
        _replace_object_name_in_landing(binding["feed_out"], old_name=old_name, new_name=new_name)
        _replace_object_name_in_landing(binding["inter_half_exit"], old_name=old_name, new_name=new_name)
        _replace_object_name_in_landing(binding["inter_half_entry"], old_name=old_name, new_name=new_name)
        _replace_object_name_in_landing(binding["series_entry"], old_name=old_name, new_name=new_name)
        _replace_object_name_in_landing(binding["series_exit"], old_name=old_name, new_name=new_name)
        return
    _replace_object_name_in_landing(binding.feed_in, old_name=old_name, new_name=new_name)
    _replace_object_name_in_landing(binding.feed_out, old_name=old_name, new_name=new_name)
    _replace_object_name_in_landing(binding.inter_half_exit, old_name=old_name, new_name=new_name)
    _replace_object_name_in_landing(binding.inter_half_entry, old_name=old_name, new_name=new_name)
    _replace_object_name_in_landing(binding.series_entry, old_name=old_name, new_name=new_name)
    _replace_object_name_in_landing(binding.series_exit, old_name=old_name, new_name=new_name)

def _replace_object_name_in_txdd_start_stub_sources(
    sources_by_board: dict[str, list[_TxDdStartStubSource]],
    *,
    old_name: str,
    new_name: str,
) -> None:
    for board_id, sources in list(sources_by_board.items()):
        updated_sources: list[_TxDdStartStubSource] = []
        for source in sources:
            if len(source) == 3:
                anchor_xyz, trace, source_object_name = source
                updated_sources.append((anchor_xyz, trace, new_name if source_object_name == old_name else source_object_name))
            else:
                anchor_xyz, trace, source_object_name, inward_dir = source
                updated_sources.append(
                    (anchor_xyz, trace, new_name if source_object_name == old_name else source_object_name, inward_dir)
                )
        sources_by_board[board_id] = updated_sources

def _live_tx_conductor_names(
    *,
    txdd_right_object_names: dict[int, str],
    group_objects: GroupObjects,
    object_names: list[str],
) -> list[str]:
    live_object_names = set(object_names)
    live = sorted(
        name
        for name in (set(txdd_right_object_names.values()) | set(group_objects["tx_vertical"]))
        if name in live_object_names
    )
    return live

def _resolve_semantic_tx_terminal_owner_name(
    *,
    terminal: _DirectedLandingSection,
    txdd_right_object_names: dict[int, str],
    group_objects: GroupObjects,
    object_names: list[str],
    final_conductor_name: str = "",
) -> str:
    live_object_names = set(object_names)
    terminal_object_name = terminal["object_name"]
    if terminal_object_name in live_object_names:
        return terminal_object_name
    role = terminal["terminal_role"]
    if role in ("feed_in", "feed_out", "inter_half_entry", "inter_half_exit"):
        names = sorted({name for name in txdd_right_object_names.values() if name in live_object_names})
    elif role in ("series_entry", "series_exit"):
        names = sorted({name for name in group_objects["tx_vertical"] if name in live_object_names})
    else:
        raise ValueError(f"tx terminal owner resolution contract violation: unsupported role {role}")
    if len(names) == 0 and final_conductor_name and final_conductor_name in live_object_names:
        return final_conductor_name
    if len(names) != 1:
        raise ValueError(
            "tx terminal owner resolution contract violation: semantic role did not resolve to exactly one live owner "
            f"(role={role}, terminal_object_name={terminal_object_name}, live_names={names})"
        )
    return names[0]

def _assert_tx_semantic_port_contract(
    *,
    binding: _TxSeriesBindingInputs | _TxSeriesChainBinding,
    txdd_right_object_names: dict[int, str],
    group_objects: GroupObjects,
    object_names: list[str],
    context: str,
) -> str:
    if isinstance(binding, dict):
        feed_in = binding["feed_in"]
        feed_out = binding["feed_out"]
    else:
        if not binding.has("feed_in"):
            raise ValueError(f"{context} feed_in terminal was not captured")
        if not binding.has("feed_out"):
            raise ValueError(f"{context} feed_out terminal was not captured")
        feed_in = binding.require("feed_in")
        feed_out = binding.require("feed_out")
    live_conductors = _live_tx_conductor_names(
        txdd_right_object_names=txdd_right_object_names,
        group_objects=group_objects,
        object_names=object_names,
    )
    if len(live_conductors) != 1:
        raise ValueError(
            f"{context} expected a single connected TX conductor before TX port creation "
            f"(live_conductors={live_conductors})"
        )
    conductor_name = live_conductors[0]
    feed_in_owner = _resolve_semantic_tx_terminal_owner_name(
        terminal=feed_in,
        txdd_right_object_names=txdd_right_object_names,
        group_objects=group_objects,
        object_names=object_names,
        final_conductor_name=conductor_name,
    )
    feed_out_owner = _resolve_semantic_tx_terminal_owner_name(
        terminal=feed_out,
        txdd_right_object_names=txdd_right_object_names,
        group_objects=group_objects,
        object_names=object_names,
        final_conductor_name=conductor_name,
    )
    if feed_in_owner != conductor_name or feed_out_owner != conductor_name:
        raise ValueError(
            f"{context} feed_in/feed_out must both resolve to the final TX conductor "
            f"(feed_in_owner={feed_in_owner}, feed_out_owner={feed_out_owner}, conductor_name={conductor_name})"
        )
    if _points_close(feed_in["center"], feed_out["center"]):
        raise ValueError(f"{context} feed_in/feed_out centers must differ")
    return conductor_name

def _replace_object_name_in_map(mapping: dict[int, str], *, old_name: str, new_name: str) -> None:
    for layer_key, object_name in list(mapping.items()):
        if object_name == old_name:
            mapping[layer_key] = new_name

def _replace_object_name_in_set_map(mapping: dict[str, set[str]], *, old_name: str, new_name: str) -> None:
    for names in mapping.values():
        if old_name in names:
            names.discard(old_name)
            names.add(new_name)


__all__ = [
    '_dedupe_names',
    '_replace_group_object_name',
    '_replace_object_name_in_list',
    '_replace_object_name_in_landing',
    '_replace_object_name_in_tx_series_binding_inputs',
    '_replace_object_name_in_txdd_start_stub_sources',
    '_live_tx_conductor_names',
    '_resolve_semantic_tx_terminal_owner_name',
    '_assert_tx_semantic_port_contract',
    '_replace_object_name_in_map',
    '_replace_object_name_in_set_map',
]
