"""mobile/app/backend/server.py

Thin compatibility wrapper.

The project already contains a fully-featured Hub implementation at the repo
root: `hub_server.py`.

This file exists so the mobile app can import/run a stable path
`mobile.app.backend.server` without duplicating server logic.
"""

from __future__ import annotations

# Re-export everything from the canonical implementation.
# (So `app` and routes behave identically.)
from hub_server import *  # noqa: F403


if __name__ == "__main__":
    # Delegate execution to the canonical entrypoint.
    import hub_server as _hub_server

    _hub_server.__dict__.get("__main__", None)
    # Run the same behavior as: python hub_server.py
    # (Hub server file guards itself under `if __name__ == "__main__":`.)
    raise SystemExit("Run: python hub_server.py")

