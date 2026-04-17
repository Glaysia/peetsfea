from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Callable, Literal, Protocol, TypedDict, cast

from peetsfea.aedt import Hfss
from peetsfea.aedt import Object3d
from peetsfea.aedt import Modeler3D

from peetsfea.backend.pyaedt.failfast import raise_on_false
from peetsfea.identity.hashing import object_name_tag_from_design_id
from peetsfea.types.manifest import (
    CadProbe,
    CoilPolaritySpec,
    EmContext,
    EmEndpoints,
    EmPortAssignmentEntry,
    EmPortAssignments,
    EmPorts,
    EmReadyObjects,
    GroupEndpointEntry,
    GroupObjects,
    RegionViolation,
    SceneObjectEntry,
)

from ..build_state import (
    BridgeAnchor,
    DdHalfGeometryCapture,
    DirectedLandingSection,
    NO_DD_PAIR_INDEX,
    OrderedTerminalSection,
    TxSeriesChainBinding,
    TxSeriesBindingInputs,
    _unset_bridge_anchor,
    _unset_directed_landing_section,
    _unset_edge2p,
    _unset_ordered_terminal_section,
    _unset_selection_key,
    _unset_string,
    _unset_tx_series_binding,
    require_state,
    state_is_set,
)
from ..rules.cad_probe import _object_name, _probe_cad_object
from ..rules.debug_checks import _bbox_violations
from ..rules.solid_ops import safe_unite


_Point3 = tuple[float, float, float]
_Edge2P = tuple[_Point3, _Point3]
_BoardKey = tuple[str, int]
_TxVerticalLinkNode = tuple[int, str, _Point3, _Point3, float, float, float, _Edge2P, _Edge2P]
_BackConnectStubSource = tuple[str, int, str, _Point3, float, str] | tuple[str, int, str, _Point3, float, str, _Point3]
_TxDdStartStubSource = tuple[_Point3, float, str] | tuple[_Point3, float, str, _Point3]
_RxDdBackStubSource = _BackConnectStubSource
_OrderedTerminalSection = OrderedTerminalSection
_BridgeAnchor = BridgeAnchor
_DirectedLandingSection = DirectedLandingSection
_DdHalfGeometryCapture = DdHalfGeometryCapture
_TxSeriesChainBinding = TxSeriesChainBinding
_TxSeriesBindingInputs = TxSeriesBindingInputs
_ZX_PLANE_NORMAL: _Point3 = (0.0, -1.0, 0.0)
_RegionKind = Literal["tx_region_dd", "tx_region_vertical", "rx_region_actual"]
TX_DD_START_STUB_LEN_MM = 1.0
TX_DD_START_STUB_LEN_BELOW_MM = 5.0
TX_VERTICAL_START_STUB_LEN_MM = 1.0
RX_DD_BACK_STUB_LEN_MM = 3.0
RX_DD_CONNECT_STUB_LEN_MM = 1.0
RX_DD_BACK_STUB_AXIS_SIGN_X = -1.0
FR4_SUBTRACT_OVERLAP_MM = 0.1
RX_DD_CONNECT_ENDPOINT_LABELS: tuple[str, str] = ("d", "B")
RX_DD_PORT_ENDPOINT_LABELS: tuple[str, str] = ("A", "c")
_NUMERIC_PORT_NAME_PATTERN = re.compile(r"^(?P<index>\d+)(?:_T\d+)?$")


class _BoundaryModule(Protocol):
    def AssignLumpedPort(self, props: list[object]) -> bool: ...

    def GetBoundaries(self) -> list[object] | tuple[object, ...]: ...

__all__ = [
    'math',
    're',
    'Path',
    'Callable',
    'Literal',
    'Protocol',
    'TypedDict',
    'cast',
    'Hfss',
    'Object3d',
    'Modeler3D',
    'raise_on_false',
    'object_name_tag_from_design_id',
    'CadProbe',
    'CoilPolaritySpec',
    'EmContext',
    'EmEndpoints',
    'EmPortAssignmentEntry',
    'EmPortAssignments',
    'EmPorts',
    'EmReadyObjects',
    'GroupEndpointEntry',
    'GroupObjects',
    'RegionViolation',
    'SceneObjectEntry',
    'BridgeAnchor',
    'DdHalfGeometryCapture',
    'DirectedLandingSection',
    'NO_DD_PAIR_INDEX',
    'OrderedTerminalSection',
    'TxSeriesChainBinding',
    'TxSeriesBindingInputs',
    '_unset_bridge_anchor',
    '_unset_directed_landing_section',
    '_unset_edge2p',
    '_unset_ordered_terminal_section',
    '_unset_selection_key',
    '_unset_string',
    '_unset_tx_series_binding',
    'require_state',
    'state_is_set',
    '_object_name',
    '_probe_cad_object',
    '_bbox_violations',
    'safe_unite',
    '_Point3',
    '_Edge2P',
    '_BoardKey',
    '_TxVerticalLinkNode',
    '_BackConnectStubSource',
    '_TxDdStartStubSource',
    '_RxDdBackStubSource',
    '_OrderedTerminalSection',
    '_BridgeAnchor',
    '_DirectedLandingSection',
    '_DdHalfGeometryCapture',
    '_TxSeriesChainBinding',
    '_TxSeriesBindingInputs',
    '_ZX_PLANE_NORMAL',
    '_RegionKind',
    'TX_DD_START_STUB_LEN_MM',
    'TX_DD_START_STUB_LEN_BELOW_MM',
    'TX_VERTICAL_START_STUB_LEN_MM',
    'RX_DD_BACK_STUB_LEN_MM',
    'RX_DD_CONNECT_STUB_LEN_MM',
    'RX_DD_BACK_STUB_AXIS_SIGN_X',
    'FR4_SUBTRACT_OVERLAP_MM',
    'RX_DD_CONNECT_ENDPOINT_LABELS',
    'RX_DD_PORT_ENDPOINT_LABELS',
    '_NUMERIC_PORT_NAME_PATTERN',
    '_BoundaryModule',
]
