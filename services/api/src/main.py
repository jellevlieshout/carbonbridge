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
    methods = ", ".join(route.methods) if hasattr(route, "methods") else "Any"
    logger.info(f"{route.path} [{methods}]")
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
