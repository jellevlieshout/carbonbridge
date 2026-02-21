import os
from contextlib import asynccontextmanager
from pathlib import Path

import conf
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import fake_registry
from routes.base import router
from utils import log

from clients.couchbase import check_connection

log.init(conf.get_log_level())
logger = log.get_logger(__name__)


def _init_observability() -> None:
    """
    Wire LangSmith tracing for Pydantic AI agents via OpenTelemetry.
    Gracefully no-ops if the required packages or env vars are absent.

    Key env vars (any one is enough):
      LANGSMITH_API_KEY  — preferred name
      LANGSMITH_PROJECT  — project name (string, NOT UUID); defaults to "carbonbridge"
    """
    api_key = os.environ.get("LANGSMITH_API_KEY")
    if not api_key:
        logger.info("LANGSMITH_API_KEY not set — agent tracing disabled")
        return

    # Always set canonical name so langsmith SDK picks it up regardless of alias
    os.environ["LANGSMITH_API_KEY"] = api_key

    project = os.environ.get("LANGSMITH_PROJECT", "carbonbridge")
    # Guard: if someone accidentally set this to a UUID, reset to name
    import re

    if re.fullmatch(r"[0-9a-f-]{36}", project):
        logger.warning(
            "LANGSMITH_PROJECT looks like a UUID (%s). "
            "LangSmith expects a project NAME string, not an ID. "
            "Falling back to 'carbonbridge'.",
            project,
        )
        project = "carbonbridge"
        os.environ["LANGSMITH_PROJECT"] = project

    try:
        from langsmith.integrations.otel import configure as langsmith_configure
        from pydantic_ai import Agent

        langsmith_configure(project_name=project)
        Agent.instrument_all()
        logger.info("LangSmith tracing enabled — project: '%s'", project)
    except ImportError as exc:
        logger.warning(
            "langsmith/pydantic_ai not installed — tracing disabled: %s", exc
        )
    except Exception as exc:
        logger.warning("Failed to initialize LangSmith tracing: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check database connection
    logger.info("Verifying Couchbase connection...")
    await check_connection()
    logger.info("Couchbase connection verified.")

    # Initialize auth client if enabled
    if conf.USE_AUTH:
        from utils import auth

        app.state.auth_client = auth.AuthClient(conf.get_auth_config())
    else:
        logger.warning("Authentication is disabled (set USE_AUTH to enable)")

    # Initialize agent observability (LangSmith tracing via OTel)
    _init_observability()
    # Log agent availability
    logger.info("Autonomous buyer agent: Gemini (Pydantic AI) mode enabled")

    # Initialize agent scheduler
    from agent.scheduler import init_scheduler, shutdown_scheduler

    init_scheduler()

    yield

    # Shutdown agent scheduler
    shutdown_scheduler()


app = FastAPI(
    title="Backend API",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
    debug=conf.get_http_expose_errors(),
)

app.include_router(router)
app.include_router(fake_registry.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not conf.validate():
    raise ValueError("Invalid configuration.")

http_conf = conf.get_http_conf()
logger.info(f"Starting API on port {http_conf.port}")

# Log all registered routes to help debug routing issues
logger.info("--- Registered Routes ---")
for route in app.routes:
    methods_set = getattr(route, "methods", None)
    methods = ", ".join(methods_set) if methods_set else "Any"
    path = getattr(route, "path", "<unknown>")
    logger.info(f"{path} [{methods}]")
logger.info("-------------------------")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=http_conf.host,
        port=http_conf.port,
        reload=http_conf.autoreload,
        log_level="info",
        reload_dirs=[str(Path(__file__).parent), "/models", "/clients"],
        log_config=None,
    )
