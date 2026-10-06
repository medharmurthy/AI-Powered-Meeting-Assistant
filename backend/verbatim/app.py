from __future__ import annotations

from verbatim.main import app
from verbatim.routes import attach_phase5_routes

# Attach Phase 5 routes (SSE, exports, samples, reruns, background workers)
attach_phase5_routes(app)

__all__ = ["app"]
