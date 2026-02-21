# CarbonBridge Project Instructions

This project runs in a Polytope-orchestrated environment. Polytope manages Docker containers for various services.

## Development Environment
- **Polytope**: Orchestrates Docker containers.
- **MCP Server**: When running `pt run stack --mcp`, the coding agent can access container information and execute commands through the Polytope MCP server.
- **Executing Commands**: Running commands (build, test, etc.) should ideally happen through the MCP `mcp_polytope_exec` tool within the relevant container.
- **Hot-Reloading**: Most changes are hot-reloaded (except for `polytope.yml` and environment variables).
- **Restarting**: If you modify `polytope.yml` or `.env` files, ask the user to restart Polytope.

## Project Structure
- `models`: Contains data models, entities, and operations.
- `services`: Contains services such as the `api` (FastAPI) and `web-app` (React Router).
- `clients`: Generated clients for services.
- `polytope.yml`: Polytope stack configuration.

## Polytope Tools
You can use the following tools via the Polytope MCP server:
- `stack`: Runs the project services defined in `polytope.yml`.
- `initialize_session`: **Always** call this first to setup the development context.
- `api-add` / `web-app-add`: Add packages to backend or frontend.
- `psql`: Open a PostgreSQL shell.
- `pgweb`: Web-based database browser (available at http://localhost:8081).
- `config-manager`: Manage database/topic configuration.
- `mcp_polytope_exec`: Execute commands directly inside running containers.
- `api-add-couchbase-client` / `api-add-temporal-client`: Extend backend with specific capabilities.
