"""Vercel Python serverless entry point.

Vercel serves this module's `app` (an ASGI app) for requests rewritten to
`/api/*` (see vercel.json). The validated analytics backend lives in
`backend/app` and is mounted here under `/api`, so its routes (`/summary`,
`/exposure`, ...) are reachable at `/api/summary`, `/api/exposure`, etc. --
exactly what the frontend calls in production.

Nothing about the analytics or the frontend changes for deployment; this file
is the only deployment-specific shim.
"""
import os
import sys

# Make the `app` package (backend/app) importable. The backend tree is force-
# included in the function bundle via `includeFiles` in vercel.json.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi import FastAPI
from app.main import app as analytics_app

app = FastAPI()
app.mount("/api", analytics_app)
