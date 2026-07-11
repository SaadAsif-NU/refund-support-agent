"""HTTP and WebSocket routes, grouped by concern.

  * pages      - the customer chat and admin dashboard HTML pages
  * api        - the read-only JSON endpoints (config, CRM, policy, ledger, health)
  * websockets - the customer chat and admin reasoning-stream channels

Each module exposes an `APIRouter` named `router`; main.py includes them.
"""
