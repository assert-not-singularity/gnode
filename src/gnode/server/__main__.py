"""Entry point: ``python -m gnode.server`` (uvicorn on 127.0.0.1:8080)."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("gnode.server.app:app", host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()
