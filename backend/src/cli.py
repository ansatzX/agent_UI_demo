"""CLI — `uv run agent-demo serve`"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys


def _get_app():
    """Import the FastAPI app, handling dev and installed paths."""
    from src.main import app  # type: ignore[import-untyped]
    return app


def serve(args: argparse.Namespace) -> None:
    """Start the server."""
    import uvicorn

    app = _get_app()
    host = args.host or os.getenv("HOST", "0.0.0.0")
    port = int(args.port or os.getenv("PORT", "8000"))

    print(f"  AI 智能助手 → http://{host}:{port}")
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        reload=not args.no_reload,
        log_level=args.log_level or "info",
    )
    server = uvicorn.Server(config)

    def _shutdown(*_args):
        server.should_exit = True

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    server.run()


def main() -> None:
    parser = argparse.ArgumentParser(prog="agent-demo")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("serve", help="启动服务器")
    p.add_argument("--host", default=None)
    p.add_argument("--port", default=None)
    p.add_argument("--no-reload", action="store_true")
    p.add_argument("--log-level", default=None)
    p.set_defaults(func=serve)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
