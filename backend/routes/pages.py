"""Page routes: the customer chat UI and the admin dashboard.

Both pages are the built React app (Vite output in ``frontend/dist``). During
active development, run the Vite dev server instead (``npm run dev``) which
serves the pages on :5173 and proxies /api and /ws back to this backend.
"""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, Response

from ..paths import DIST_DIR

router = APIRouter()

_NOT_BUILT = (
    "<h1>Frontend not built</h1>"
    "<p>The React frontend hasn't been built yet. From <code>frontend/</code> run "
    "<code>npm install &amp;&amp; npm run build</code> — or use the Vite dev server "
    "(<code>npm run dev</code>) and open "
    "<a href='http://localhost:5173'>http://localhost:5173</a>.</p>"
)


def _serve(page: str) -> Response:
    file = DIST_DIR / page
    if not file.exists():
        return HTMLResponse(_NOT_BUILT, status_code=503)
    return FileResponse(file)


@router.get("/")
async def customer_page() -> Response:
    return _serve("index.html")


@router.get("/admin")
async def admin_page() -> Response:
    return _serve("admin.html")
