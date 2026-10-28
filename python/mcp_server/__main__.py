"""MCP server entry point.

Usage:
    python -m python.mcp_server --transport stdio
    python -m python.mcp_server --transport http --host 0.0.0.0 --port 8765
"""
import argparse
import logging
import sys

from python.mcp_server.auth import BearerAuthMiddleware, get_api_key
from python.mcp_server.server import mcp

logger = logging.getLogger("mcp_server")


def _run_stdio() -> None:
    mcp.run(transport="stdio")


def _run_http(host: str, port: int) -> None:
    import uvicorn

    app = mcp.streamable_http_app()
    api_key = get_api_key()
    if api_key is None:
        logger.warning(
            "MCP_API_KEY is not set. The HTTP endpoint is UNAUTHENTICATED. "
            "Set MCP_API_KEY in the environment before exposing this server."
        )
    else:
        app.add_middleware(BearerAuthMiddleware, api_key=api_key)
        logger.info("Bearer auth enabled (MCP_API_KEY detected).")

    uvicorn.run(app, host=host, port=port)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="stockManegement MCP server")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="Transport: stdio (local clients) or http (remote / mobile clients)",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    if args.transport == "stdio":
        _run_stdio()
    else:
        _run_http(args.host, args.port)


if __name__ == "__main__":
    main(sys.argv[1:])
