"""FastAPI application.

Composition root: creates the app, wires up the route groups (pages, JSON APIs,
and the reasoning-stream WebSockets), and mounts the frontend's static assets.
The actual handlers live in the `routes` package; per-concern logic lives in
`agent`, `store`, and `events`.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .paths import DIST_DIR
from .routes import api, pages, websockets

app = FastAPI(title="NimbusMart AI Refund Support Agent")

app.include_router(pages.router)
app.include_router(api.router)
app.include_router(websockets.router)


class _BuiltAssets(StaticFiles):
    """Static files that tolerate a missing directory.

    `check_dir=False` only skips Starlette's constructor-time check; its first-request
    `check_config` still raises `RuntimeError` (a 500) when the directory is absent.
    Skipping that check while the directory does not exist makes a request for an
    asset a plain 404 until the frontend is built, which is what the pages route
    (a 503 "Frontend not built" page) and the tests expect.
    """

    async def check_config(self) -> None:
        if self.directory is not None and not os.path.isdir(str(self.directory)):
            return
        await super().check_config()


# Serve the built React app's hashed JS/CSS (Vite output in frontend/dist/assets).
# The server starts, and asset requests 404, until the first `npm run build`.
app.mount("/assets", _BuiltAssets(directory=DIST_DIR / "assets", check_dir=False), name="assets")
