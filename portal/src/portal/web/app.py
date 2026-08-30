"""FastAPI app — the web replacement for the Excel authoring workbook.

Run locally with: `uv run uvicorn portal.web.app:app --reload` (from the `portal/` directory).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .deps import BASE_DIR
from .routers import (
    basin_conventions,
    batteries,
    buses,
    cases,
    generate,
    lines,
    plants,
    projects,
    stages,
    thermal_costs,
)

app = FastAPI(title="PLP Case Portal")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(cases.router)
app.include_router(buses.router)
app.include_router(lines.router)
app.include_router(stages.router)
app.include_router(plants.router)
app.include_router(batteries.router)
app.include_router(projects.router)
app.include_router(thermal_costs.router)
app.include_router(basin_conventions.router)
app.include_router(generate.router)
