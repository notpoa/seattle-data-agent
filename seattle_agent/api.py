"""FastAPI boundary. Health distinguishes server health from data readiness."""

from typing import Annotated

from fastapi import FastAPI, Path, Request
from fastapi.responses import JSONResponse

from .models import Query, Search
from .query import QueryError
from .tools import DataTools, DataUnavailable, PendingSeattleTools


def create_app(tools: DataTools | None = None) -> FastAPI:
    app = FastAPI(title="Seattle Data Agent", version="0.1.0")
    data_tools = tools if tools is not None else PendingSeattleTools()

    @app.exception_handler(DataUnavailable)
    async def unavailable(_request: Request, exc: DataUnavailable):
        return JSONResponse(status_code=503, content={"error": "data_unavailable", "detail": str(exc)})

    @app.exception_handler(QueryError)
    async def invalid_query(_request: Request, exc: QueryError):
        return JSONResponse(status_code=422, content={"error": "invalid_query", "detail": str(exc)})

    @app.get("/health")
    def health():
        return {"status": "ok", "live_data_enabled": False, "agent_enabled": False,
                "stage": "offline query foundation; live integration pending"}

    @app.post("/api/datasets/search")
    def search(request: Search):
        return data_tools.search(request)

    @app.get("/api/datasets/{dataset_id}")
    def inspect(dataset_id: Annotated[str, Path(pattern=r"^[a-z0-9]{4}-[a-z0-9]{4}$")]):
        return data_tools.inspect(dataset_id)

    @app.post("/api/query")
    def query(request: Query):
        return data_tools.query(request)

    return app


app = create_app()
