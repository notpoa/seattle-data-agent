"""Compile a small structured query language, never arbitrary SQL.

Current Socrata query/function documentation reviewed; legacy public resource
queries verified against Seattle. No network calls in this compiler.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from .models import Query, Schema


class QueryError(ValueError):
    pass


NUMERIC = {"number", "money", "double"}
DATES = {"calendar_date", "floating_timestamp", "fixed_timestamp"}
OPERATORS = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


def literal(value, data_type: str) -> str:
    if data_type in NUMERIC:
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            raise QueryError("Numeric fields require a finite numeric value")
        try:
            number = Decimal(str(value))
        except InvalidOperation as exc:
            raise QueryError("Invalid numeric value") from exc
        if not number.is_finite():
            raise QueryError("Numeric values must be finite")
        return str(number)
    if data_type == "checkbox":
        if not isinstance(value, bool):
            raise QueryError("Boolean fields require true or false")
        return "true" if value else "false"
    if data_type in DATES:
        if not isinstance(value, str):
            raise QueryError("Date fields require ISO date/time strings")
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise QueryError("Invalid ISO date/time") from exc
    elif data_type != "text":
        raise QueryError(f"Filtering type {data_type!r} is not supported")
    if not isinstance(value, str):
        raise QueryError("Text fields require strings")
    return "'" + value.replace("'", "''") + "'"


def compile_query(query: Query, schema: Schema) -> dict[str, str]:
    if schema.dataset_id != query.dataset_id:
        raise QueryError("Query and inspected schema refer to different datasets")
    if schema.asset_type != "dataset":
        raise QueryError("Only native tabular datasets are supported; external GIS, files, and other assets are unsupported")
    fields = {column.name: column for column in schema.columns}

    def require_field(name: str):
        if name not in fields:
            raise QueryError(f"Field {name!r} was not present in the inspected schema")
        return fields[name]

    selected = query.columns or query.group_by
    for name in selected:
        require_field(name)
    group_expressions = list(query.group_by)
    selection_expressions = list(selected)
    if query.time_bucket:
        if 'period' in selected:
            raise QueryError("Group field 'period' conflicts with the time alias")
        field = require_field(query.time_bucket.field)
        if field.data_type not in {"calendar_date", "floating_timestamp"}:
            raise QueryError("Time buckets currently require a floating/calendar timestamp")
        # Avoid quietly comparing a partial year with a complete year.
        operators = {f.operator for f in query.filters if f.field == query.time_bucket.field}
        if not {'gte', 'lt'} <= operators:
            raise QueryError("Trends require an explicit start (gte) and exclusive end (lt) date")
        try:
            starts = [datetime.fromisoformat(f.value) for f in query.filters if f.field == query.time_bucket.field and f.operator == 'gte']
            ends = [datetime.fromisoformat(f.value) for f in query.filters if f.field == query.time_bucket.field and f.operator == 'lt']
            if max(starts) >= min(ends):
                raise QueryError('Trend start must be earlier than the exclusive end')
        except (ValueError, TypeError) as exc:
            raise QueryError('Trends require valid, compatible ISO start and end dates') from exc
        function = 'date_trunc_ym' if query.time_bucket.interval == 'month' else 'date_trunc_y'
        expression = f"{function}({query.time_bucket.field})"
        group_expressions.append(expression)
        selection_expressions.append(f"{expression} AS period")
    if query.metric:
        if "value" in query.group_by:
            raise QueryError("Group field 'value' conflicts with the metric alias")
        metric = query.metric
        if metric.operation == "count":
            expression = "count(*) AS value"
        elif metric.operation == "count_distinct":
            require_field(metric.field)
            expression = f"count(distinct {metric.field}) AS value"
        else:
            field = require_field(metric.field)
            if field.data_type not in NUMERIC:
                raise QueryError("Metrics other than row count currently require numeric fields")
            expression = f"{metric.operation}({metric.field}) AS value"
        select = ", ".join([*selection_expressions, expression])
    else:
        select = ", ".join(selected)
    # One extra row detects output truncation. No pagination or whole-dataset export.
    params = {"$select": select, "$limit": str(query.limit + 1)}
    if group_expressions:
        params["$group"] = ", ".join(group_expressions)
    clauses = []
    for condition in query.filters:
        field = require_field(condition.field)
        if condition.operator in {"is_null", "not_null"}:
            operator = "IS NULL" if condition.operator == "is_null" else "IS NOT NULL"
            clauses.append(f"{condition.field} {operator}")
        else:
            if condition.operator not in {"eq", "ne"} and field.data_type not in NUMERIC | DATES:
                raise QueryError("Range comparisons require numeric or date fields")
            clauses.append(f"{condition.field} {OPERATORS[condition.operator]} {literal(condition.value, field.data_type)}")
    if clauses:
        params["$where"] = " AND ".join(clauses)
    if query.order_by:
        allowed = {*selected, *(["value"] if query.metric else []), *(["period"] if query.time_bucket else [])}
        if query.order_by.field not in allowed:
            raise QueryError("Sort field must appear in the result")
        params["$order"] = f"{query.order_by.field} {query.order_by.direction.upper()}"
    elif query.time_bucket:
        params["$order"] = "period ASC"
    return params
