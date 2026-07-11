"""Convenience launcher: `python run.py` (equivalent to running uvicorn)."""
import os

import uvicorn

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  NimbusMart AI Refund Agent")
    print(f"  Customer chat : http://{host}:{port}/")
    print(f"  Admin console : http://{host}:{port}/admin\n")
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
