"""
Backwards-compatibility shim.
The scheduler has moved to agents/buyer/scheduler.py.
"""
from agents.buyer.scheduler import init_scheduler, shutdown_scheduler  # noqa: F401

__all__ = ["init_scheduler", "shutdown_scheduler"]
