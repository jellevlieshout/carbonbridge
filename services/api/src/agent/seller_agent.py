"""
Backwards-compatibility shim.
The seller agent has moved to agents/seller/agent.py.
"""
from agents.seller.agent import run_seller_advisory_agent  # noqa: F401

__all__ = ["run_seller_advisory_agent"]
