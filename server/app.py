"""FastAPI application for the Supermail environment."""

try:
    from openenv.core.env_server.http_server import create_app
except Exception as exc:  # pragma: no cover
    raise ImportError(
        "openenv-core is required to run the server. Install dependencies first."
    ) from exc

try:
    from ..models import SupportAction, SupportObservation
    from .environment import SupermailEnvironment
except ImportError:  # pragma: no cover
    from models import SupportAction, SupportObservation
    from server.environment import SupermailEnvironment


app = create_app(
    SupermailEnvironment,
    SupportAction,
    SupportObservation,
    env_name="supermail",
    max_concurrent_envs=4,
)


def _run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the HTTP server directly."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


def main() -> None:
    """CLI entry point used by OpenEnv validation and local runs."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    _run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
