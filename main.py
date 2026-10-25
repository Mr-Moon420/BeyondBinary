# main.py
"""
BeyondBinary Application Entrypoint.
Exposes the FastAPI application instance from the backend package.
Enables backward-compatible invocation via:
    `uvicorn main:app`
    `uvicorn backend.main:app`
    `python main.py`
"""

import os
import sys

# Ensure root and backend directories are on Python search path
_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.join(_ROOT_DIR, "backend")

if _ROOT_DIR not in sys.path:
    sys.path.insert(0, _ROOT_DIR)
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from backend.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run("main:app", host="127.0.0.1", port=port, reload=True)
