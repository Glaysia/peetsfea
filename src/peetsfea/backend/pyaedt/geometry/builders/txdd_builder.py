from __future__ import annotations

from .txdd_planner import build_txdd_realizations
from .txdd_right_capture import capture_txdd_right_half
from .txdd_types import TxDdBuildRequest


def build_for_board(request: TxDdBuildRequest) -> None:
    if request.pcb["id"] not in request.finalize_inputs.txdd_start_stub_sources:
        request.finalize_inputs.txdd_start_stub_sources[request.pcb["id"]] = []
    for realization in build_txdd_realizations(request):
        capture_txdd_right_half(request, realization)
