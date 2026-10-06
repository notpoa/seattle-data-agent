import pytest
from pydantic import ValidationError

from seattle_agent.models import Query, Search
from seattle_agent.query import QueryError, compile_query


def test_grouped_ranking_with_explicit_time_window(schema):
    request = Query.model_validate({
        "dataset_id": "abcd-1234", "group_by": ["area"], "metric": {"operation": "count"},
        "filters": [
            {"field": "recorded_at", "operator": "gte", "value": "2025-01-01"},
            {"field": "recorded_at", "operator": "lt", "value": "2026-01-01"},
        ], "order_by": {"field": "value", "direction": "desc"}, "limit": 5,
    })
    assert compile_query(request, schema) == {
        "$select": "area, count(*) AS value", "$group": "area", "$limit": "6",
        "$order": "value DESC",
        "$where": "recorded_at >= '2025-01-01' AND recorded_at < '2026-01-01'",
    }


@pytest.mark.parametrize("operation", ["sum", "avg", "min", "max"])
def test_numeric_metrics(schema, operation):
    result = compile_query(Query(dataset_id="abcd-1234", metric={"operation": operation, "field": "amount"}), schema)
    assert result["$select"] == f"{operation}(amount) AS value"


def test_string_literal_cannot_escape_into_expression(schema):
    request = Query(dataset_id="abcd-1234", columns=["area"], filters=[
        {"field": "area", "operator": "eq", "value": "O'Brien' OR 1=1 --"},
    ])
    assert compile_query(request, schema)["$where"] == "area = 'O''Brien'' OR 1=1 --'"


@pytest.mark.parametrize("change", [
    {"dataset_id": "https://evil.example/abcd-1234"},
    {"columns": ["area;drop table x"]}, {"limit": 0}, {"limit": 101}, {"limit": True},
    {"sql": "SELECT *"}, {"columns": []}, {"group_by": ["area"]},
    {"columns": ["area", "area"]},
    {"filters": [{"field": "area", "operator": "eq", "value": "x\\' OR 1=1"}]},
    {"filters": [{"field": "area", "operator": "eq", "value": "x\nOR 1=1"}]},
    {"filters": [{"field": "area", "operator": "eq"}]},
    {"filters": [{"field": "area", "operator": "is_null", "value": "x"}]},
])
def test_invalid_arguments_rejected(change):
    with pytest.raises(ValidationError):
        Query.model_validate({"dataset_id": "abcd-1234", "columns": ["area"], **change})


@pytest.mark.parametrize("query_args", [
    {"columns": ["invented_field"]},
    {"metric": {"operation": "sum", "field": "area"}},
    {"columns": ["area"], "order_by": {"field": "amount"}},
    {"columns": ["area"], "filters": [{"field": "amount", "operator": "eq", "value": "0 OR 1=1"}]},
    {"columns": ["area"], "filters": [{"field": "amount", "operator": "eq", "value": True}]},
    {"columns": ["area"], "filters": [{"field": "amount", "operator": "eq", "value": "NaN"}]},
    {"columns": ["area"], "filters": [{"field": "recorded_at", "operator": "eq", "value": "yesterday"}]},
    {"columns": ["area"], "filters": [{"field": "active", "operator": "eq", "value": "true"}]},
    {"columns": ["area"], "filters": [{"field": "shape", "operator": "eq", "value": "POINT (0 0)"}]},
    {"columns": ["area"], "filters": [{"field": "area", "operator": "gt", "value": "A"}]},
])
def test_schema_semantic_errors(schema, query_args):
    with pytest.raises(QueryError):
        compile_query(Query(dataset_id="abcd-1234", **query_args), schema)


@pytest.mark.parametrize("asset_type", ["map", "file", "external", "chart"])
def test_unsupported_assets(schema, asset_type):
    schema.asset_type = asset_type
    with pytest.raises(QueryError, match="external GIS"):
        compile_query(Query(dataset_id="abcd-1234", columns=["area"]), schema)


def test_schema_identity_required(schema):
    with pytest.raises(QueryError, match="different datasets"):
        compile_query(Query(dataset_id="xxxx-yyyy", columns=["area"]), schema)


def test_null_and_boolean_filters(schema):
    result = compile_query(Query(dataset_id="abcd-1234", columns=["area"], filters=[
        {"field": "area", "operator": "not_null"},
        {"field": "active", "operator": "eq", "value": True},
    ]), schema)
    assert result["$where"] == "area IS NOT NULL AND active = true"


def test_blank_discovery_rejected():
    with pytest.raises(ValidationError):
        Search(text="   ")
