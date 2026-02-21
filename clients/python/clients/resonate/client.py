"""Resonate Client — wraps the resonate-sdk for centralised instance management.

All Resonate instance-level operations (creation, worker registration, start,
RPC invocation, promise cancellation, dependency injection) go through this
client. Workflow-level context operations (ctx.lfc, ctx.sleep, etc.) remain
SDK-native since they belong to registered workflow functions.
"""

import logging
from typing import Any, Callable, Optional

from resonate import Resonate, Context
from clients.resonate.exceptions import (
    ResonateClientError,
    ResonateConnectionError,
    ResonateRPCError,
)

logger = logging.getLogger(__name__)


class ResonateClient:
    """Thin wrapper around a remote Resonate instance.

    Usage::

        client = ResonateClient(host="http://resonate:8001", group="my-worker")
        
        @client.register
        def my_workflow(ctx: Context):
            ...

        client.set_dependency("key", value)
        client.start()
    """

    def __init__(self, host: str, group: str) -> None:
        """Create a remote Resonate instance.

        Args:
            host: URL of the Resonate server (e.g. ``http://resonate:8001``).
            group: Worker group name for task routing.
        """
        self.host = host
        self.group = group
        self._instance: Resonate = Resonate.remote(host=host, group=group)

    # ------------------------------------------------------------------
    # Worker lifecycle
    # ------------------------------------------------------------------

    def register(self, fn: Callable) -> Callable:
        """Register a workflow function with this Resonate instance.

        Can be used as a decorator::

            @client.register
            def my_workflow(ctx: Context):
                ...
        """
        return self._instance.register(fn)

    def start(self) -> None:
        """Start the Resonate worker, begin polling for tasks."""
        self._instance.start()

    def set_dependency(self, key: str, value: Any) -> None:
        """Inject a dependency into the Resonate instance.

        Dependencies set here are retrievable inside workflows via
        ``ctx.get_dependency(key)``.
        """
        self._instance.set_dependency(key, value)

    # ------------------------------------------------------------------
    # RPC & promise management
    # ------------------------------------------------------------------

    def rpc(
        self,
        promise_id: str,
        fn_name: str,
        *,
        target: Optional[str] = None,
    ) -> Any:
        """Invoke a registered function on a (possibly remote) worker via RPC.

        Args:
            promise_id: Unique promise identifier for this invocation.
            fn_name: Name of the registered workflow function to call.
            target: Optional Resonate target URI
                    (e.g. ``poll://any@reconciliation-task``).

        Returns:
            The result of the remote function execution.
        """
        try:
            opts = self._instance
            if target:
                opts = opts.options(target=target)
            return opts.rpc(promise_id, fn_name)
        except Exception as e:
            raise ResonateRPCError(f"RPC '{fn_name}' failed: {e}") from e

    def cancel_promise(self, promise_id: str) -> None:
        """Cancel an existing Resonate promise.

        Args:
            promise_id: The promise ID to cancel.
        """
        try:
            self._instance.promises.cancel(id=promise_id)
        except Exception as e:
            raise ResonateClientError(
                f"Failed to cancel promise '{promise_id}': {e}"
            ) from e
