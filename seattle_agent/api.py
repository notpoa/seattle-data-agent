"""FastAPI boundary. Health distinguishes server health from data readiness."""

from typing import Annotated
import json
import os
from pathlib import Path as FilePath

from fastapi import FastAPI, Path, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .models import AnalysisRequest, Query, Search
from .query import QueryError
from .tools import DataTools, DataUnavailable, PendingSeattleTools
from .socrata import SeattleTools
from .agent import analyze, api_key

load_dotenv(FilePath(__file__).resolve().parents[1] / '.env', override=False)


def create_app(tools: DataTools | None = None) -> FastAPI:
    app = FastAPI(title="Seattle Data Agent", version="0.1.0")
    data_tools = tools if tools is not None else SeattleTools()
    origins = [origin.strip() for origin in os.environ.get('SEATTLE_FRONTEND_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',') if origin.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins,
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])

    @app.exception_handler(DataUnavailable)
    async def unavailable(_request: Request, exc: DataUnavailable):
        return JSONResponse(status_code=503, content={"error": "data_unavailable", "detail": str(exc)})

    @app.exception_handler(QueryError)
    async def invalid_query(_request: Request, exc: QueryError):
        return JSONResponse(status_code=422, content={"error": "invalid_query", "detail": str(exc)})

    @app.get("/health")
    def health():
        return {"status": "ok", "live_data_enabled": not isinstance(data_tools, PendingSeattleTools),
                "agent_enabled": bool(api_key()), "stage": "Seattle discovery and bounded analysis",
                "capabilities": {"trends": True, "cross_dataset_correlations": False},
                "note": "Capabilities report configured code, not live upstream connectivity or credential validity."}

    @app.post("/api/datasets/search")
    def search(request: Search):
        return data_tools.search(request)

    @app.get("/api/datasets/{dataset_id}")
    def inspect(dataset_id: Annotated[str, Path(pattern=r"^[a-z0-9]{4}-[a-z0-9]{4}$")]):
        return data_tools.inspect(dataset_id)

    @app.post("/api/query")
    def query(request: Query):
        return data_tools.query(request)

    @app.post('/api/analyze')
    def analyze_request(request: AnalysisRequest):
        def events():
            for event in analyze(request, data_tools):
                yield json.dumps(event, default=str) + '\n'
        return StreamingResponse(events(), media_type='application/x-ndjson', headers={'Cache-Control': 'no-store'})

    frontend = FilePath(__file__).resolve().parents[1] / 'frontend' / 'out'
    if frontend.is_dir():
        app.mount('/', StaticFiles(directory=frontend, html=True), name='website')
    else:
        @app.get('/', include_in_schema=False)
        def home():
            return JSONResponse(status_code=503, content={'detail': 'Website is not built yet. Run the Seattle: Set up website task, then restart the backend.'})

    return app


app = create_app()
