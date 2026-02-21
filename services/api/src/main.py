import os
import uvicorn
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from utils import log
from routes.base import router
from routes import fake_registry
import conf
from clients.couchbase import check_connection

log.init(conf.get_log_level())
logger = log.get_logger(__name__)


def _init_observability() -> None:
    """
    Wire LangSmith tracing for Pydantic AI agents via OpenTelemetry.
    Gracefully no-ops if the required packages or env vars are absent.
    """
    api_key = (
        os.environ.get("LANGSMITH_API_KEY")
        or os.environ.get("LANGSMITH_API")
    )
    if not api_key:
        logger.info("LANGSMITH_API_KEY not set — agent tracing disabled")
        return

    project = os.environ.get("LANGSMITH_PROJECT", "carbonbridge")

    try:
        from langsmith.integrations.otel import configure as langsmith_configure
        from pydantic_ai import Agent

        # Ensure the key is set in env for the SDK to pick up
        os.environ.setdefault("LANGSMITH_API_KEY", api_key)

        langsmith_configure(project_name=project)
        Agent.instrument_all()
        logger.info("LangSmith tracing enabled (project: %s)", project)
    except ImportError:
        logger.warning("langsmith or pydantic_ai not installed — tracing disabled")
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

    # Initialize agent observability
    _init_observability()

    yield

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
        log_config=None
    )
