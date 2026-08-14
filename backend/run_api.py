"""Cross-platform local API entry point."""

import asyncio

import uvicorn


def main() -> None:
    """Use a selector loop compatible with Psycopg on every supported platform."""

    configuration = uvicorn.Config(
        "jobhunter.main:app",
        host="127.0.0.1",
        port=8000,
        loop="none",
    )
    server = uvicorn.Server(configuration)
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(server.serve())


if __name__ == "__main__":
    main()
