from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict
import datetime


class ExecutionStatus(str, Enum):
    SIMULATED = "SIMULATED"
    TESTBED = "TESTBED"
    REAL = "REAL"
    NOT_EXECUTED = "NOT_EXECUTED"


@dataclass
class ExecResult:
    action: str
    status: ExecutionStatus
    timestamp: datetime.datetime
    load_before_MW: float
    load_after_MW: float
    simulated_impact_MW: float
    raw_response: Any
    verification: Dict[str, Any]
    provenance_metadata: Dict[str, Any] | None = None


class ControlAdapter:
    """Abstract control adapter interface."""

    def execute(self, action: Dict[str, Any], mode: str = "simulated") -> ExecResult:
        raise NotImplementedError()

    def verify(self, exec_result: ExecResult, timeout: int = 5) -> Dict[str, Any]:
        raise NotImplementedError()
