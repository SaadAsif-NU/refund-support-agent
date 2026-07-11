"""Shared filesystem paths."""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
# Vite build output (`npm run build` in frontend/). This is what production serves.
DIST_DIR = FRONTEND_DIR / "dist"
