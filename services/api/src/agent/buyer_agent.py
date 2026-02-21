"""
Backwards-compatibility shim.
The buyer agent has moved to agents/buyer/agent.py.
"""
from agents.buyer.agent import run_buyer_agent  # noqa: F401

__all__ = ["run_buyer_agent"]
