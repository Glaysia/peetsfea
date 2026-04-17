from __future__ import annotations

import sys

from .build_bridge_ops import *
from .build_em_artifacts import *
from .build_finalize_ops import *
from .build_fr4_ops import *
from .build_name_ops import *
from .build_port_ops import *
from .build_sheet_ops import *
from .build_common import *
from .build_terminal_ops import *
from .build_topology_ops import *
from .build_via_ops import *
from .build_tx_bridges import *
from .build_tx_terminals import *


def _sheet_ops_proxy(*args: object, **kwargs: object) -> object:
    return sys.modules[__name__].__dict__["_create_sheet_from_points"](*args, **kwargs)


_create_thickened_sheet_from_points.__globals__["_create_sheet_from_points"] = _sheet_ops_proxy
