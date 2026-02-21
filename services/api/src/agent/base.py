"""
Backwards-compatibility shim.
Base utilities have moved to agents/shared/base.py.
"""
from agents.shared.base import check_no_running_run, timed_step  # noqa: F401

__all__ = ["check_no_running_run", "timed_step"]
