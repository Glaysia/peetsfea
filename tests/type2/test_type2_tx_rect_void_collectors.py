from __future__ import annotations

import build123d as bd
import pytest

from peetsfea.type2_tx_rect_void_collectors import TxRectVoidCollectorTileInput
from peetsfea.type2_tx_rect_void_collectors import TxRectVoidColumnsCollectorBuildResult
from peetsfea.type2_tx_rect_void_collectors import build_tx_rect_void_columns_collectors


def _assert_coplanar_tab_faces(*, result: TxRectVoidColumnsCollectorBuildResult) -> None:
    start_tab_z_values = tuple(vertex[2] for vertex in result.external_tab_face_vertices.start)
    end_tab_z_values = tuple(vertex[2] for vertex in result.external_tab_face_vertices.end)
    assert len(start_tab_z_values) == 4
    assert len(end_tab_z_values) == 4
    assert start_tab_z_values == (start_tab_z_values[0],) * 4
    assert end_tab_z_values == (end_tab_z_values[0],) * 4
    assert start_tab_z_values == end_tab_z_values


def _require_role_group_tuple(*, groups: object, field_name: str) -> tuple[str, ...]:
    value = getattr(groups, field_name, None)
    assert isinstance(value, tuple), (
        f"collector label group '{field_name}' must exist on source_labels_grouped_by_role "
        f"(actual type={type(value)!r})"
    )
    return value


def _assert_pour_labels(*, value: tuple[str, ...], prefix: str, role: str, branch_count: int) -> None:
    assert len(value) == branch_count + 1, f"{role} pour labels must include one bus and one patch per branch"
    assert value[0] == f"txrvc_pour_{prefix}_bus"
    assert all(label.startswith(f"txrvc_pour_{prefix}_") for label in value)


def _box_shape(
    *,
    label: str,
    origin_xyz: tuple[float, float, float],
    size_xyz: tuple[float, float, float],
) -> bd.Shape:
    shape = bd.Box(*size_xyz, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN)).moved(
        bd.Location(origin_xyz)
    )
    shape.label = label
    return shape


def _bottom_vertices(
    *,
    origin_xyz: tuple[float, float, float],
    size_xy: tuple[float, float],
) -> tuple[tuple[float, float, float], ...]:
    origin_x, origin_y, origin_z = origin_xyz
    size_x, size_y = size_xy
    return (
        (origin_x, origin_y, origin_z),
        (origin_x + size_x, origin_y, origin_z),
        (origin_x + size_x, origin_y + size_y, origin_z),
        (origin_x, origin_y + size_y, origin_z),
    )


def _synthetic_tile_inputs(
    *,
    x_count: int,
    y_count: int,
) -> tuple[TxRectVoidCollectorTileInput, ...]:
    tile_inputs: list[TxRectVoidCollectorTileInput] = []
    for x_index in range(x_count):
        for y_index in range(y_count):
            origin_x = float(x_index) * 4.0
            origin_y = float(y_index) * 4.0
            start_origin = (origin_x + 0.2, origin_y + 0.2, -1.0)
            end_origin = (origin_x + 2.3, origin_y + 2.3, -1.0)
            tile_inputs.append(
                TxRectVoidCollectorTileInput(
                    x_index=x_index,
                    y_index=y_index,
                    tile_copper_shapes=(
                        _box_shape(
                            label=f"txrvc_x{x_index}_y{y_index}_cu_l0",
                            origin_xyz=(origin_x, origin_y, 0.0),
                            size_xyz=(3.0, 3.0, 0.2),
                        ),
                    ),
                    start_terminal_stub_shape=_box_shape(
                        label=f"txrvc_x{x_index}_y{y_index}_stub_s",
                        origin_xyz=start_origin,
                        size_xyz=(0.5, 0.5, 1.1),
                    ),
                    end_terminal_stub_shape=_box_shape(
                        label=f"txrvc_x{x_index}_y{y_index}_stub_e",
                        origin_xyz=end_origin,
                        size_xyz=(0.5, 0.5, 1.1),
                    ),
                    start_pickup_vertices=_bottom_vertices(origin_xyz=start_origin, size_xy=(0.5, 0.5)),
                    end_pickup_vertices=_bottom_vertices(origin_xyz=end_origin, size_xy=(0.5, 0.5)),
                    copper_thickness_mm=0.1,
                )
            )
    return tuple(tile_inputs)


def test_tx_rect_void_collectors_build_1x1_fused_copper_and_two_tabs() -> None:
    result = build_tx_rect_void_columns_collectors(
        connection_mode=0,
        tile_inputs=_synthetic_tile_inputs(x_count=1, y_count=1),
    )
    source_labels_grouped_by_role = result.source_labels_grouped_by_role
    start_pours = _require_role_group_tuple(groups=source_labels_grouped_by_role, field_name="start_pours")
    end_pours = _require_role_group_tuple(groups=source_labels_grouped_by_role, field_name="end_pours")

    assert result.expected_exported_body_name == "tx_rect_void_columns_copper"
    assert result.fused_copper_shape.label == "tx_rect_void_columns_copper"
    assert len(tuple(result.fused_copper_shape.solids())) == 1
    _assert_pour_labels(value=start_pours, prefix="s", role="start", branch_count=1)
    _assert_pour_labels(value=end_pours, prefix="e", role="end", branch_count=1)
    assert len(source_labels_grouped_by_role.start_external_tabs) == 1
    assert len(source_labels_grouped_by_role.end_external_tabs) == 1
    _assert_coplanar_tab_faces(result=result)


def test_tx_rect_void_collectors_build_3x3_balanced_non_intersecting_route() -> None:
    result = build_tx_rect_void_columns_collectors(
        connection_mode=0,
        tile_inputs=_synthetic_tile_inputs(x_count=3, y_count=3),
    )
    labels = tuple(shape.label for shape in result.collector_source_shapes)

    source_labels_grouped_by_role = result.source_labels_grouped_by_role
    assert len(labels) == len(set(labels))
    _assert_pour_labels(
        value=_require_role_group_tuple(groups=source_labels_grouped_by_role, field_name="start_pours"),
        prefix="s",
        role="start",
        branch_count=9,
    )
    _assert_pour_labels(
        value=_require_role_group_tuple(groups=source_labels_grouped_by_role, field_name="end_pours"),
        prefix="e",
        role="end",
        branch_count=9,
    )
    assert len(source_labels_grouped_by_role.end_layer_drops) == result.branch_balance_audit.branch_count
    assert result.branch_balance_audit.branch_count == 9
    assert result.branch_balance_audit.balance_delta_mm <= result.branch_balance_audit.tolerance_mm
    assert result.branch_balance_audit.max_branch_total_delta_mm <= result.branch_balance_audit.branch_spread_limit_mm
    assert result.overlap_audit.positive_volume_pair_count == 0
    assert result.overlap_audit.max_intersection_volume_mm3 <= result.overlap_audit.tolerance_mm3


def test_tx_rect_void_collectors_reject_series_mode() -> None:
    with pytest.raises(RuntimeError, match=r"only support connection_mode=0"):
        build_tx_rect_void_columns_collectors(
            connection_mode=1,
            tile_inputs=_synthetic_tile_inputs(x_count=1, y_count=1),
        )
