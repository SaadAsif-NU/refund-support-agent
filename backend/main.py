"""FastAPI application.

Composition root: creates the app, wires up the route groups (pages, JSON APIs,
and the reasoning-stream WebSockets), and mounts the frontend's static assets.
The actual handlers live in the `routes` package; per-concern logic lives in
`agent`, `store`, and `events`.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .paths import DIST_DIR
from .routes import api, pages, websockets

app = FastAPI(title="NimbusMart AI Refund Support Agent")

app.include_router(pages.router)
app.include_router(api.router)
app.include_router(websockets.router)

# Serve the built React app's hashed JS/CSS (Vite output in frontend/dist/assets).
# check_dir=False lets the server start even before the first `npm run build`;
# asset requests simply 404 until the frontend is built.
app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets", check_dir=False), name="assets")
