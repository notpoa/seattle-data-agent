"""Contracts shared by the API, CLI, and eventual model tools.

Models cannot provide SQL fragments, URLs, executable code, or fabricated sources.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, StrictStr, model_validator

DatasetId = Annotated[str, Field(pattern=r"^[a-z0-9]{4}-[a-z0-9]{4}$")]
ColumnName = Annotated[str, Field(pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$", max_length=128)]
Scalar = StrictStr | StrictInt | StrictFloat | StrictBool


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Column(Contract):
    name: ColumnName
    label: str
    data_type: str
    description: str | None = None
    observed_min: str | None = None
    observed_max: str | None = None


class Schema(Contract):
    dataset_id: DatasetId
    title: str
    description: str
    asset_type: str
    columns: list[Column]
    updated_at: datetime | None = None
    # Unknown must remain unknown; a title is not evidence of row grain or coverage.
    row_definition: str | None = None
    coverage_notes: str | None = None

    @model_validator(mode="after")
    def unique_columns(self):
        if len({column.name for column in self.columns}) != len(self.columns):
            raise ValueError("Schema contains duplicate field names")
        return self


class Filter(Contract):
    field: ColumnName
    operator: Literal["eq", "ne", "gt", "gte", "lt", "lte", "is_null", "not_null"]
    value: Scalar | None = None

    @model_validator(mode="after")
    def check_value(self):
        null_operator = self.operator in {"is_null", "not_null"}
        if null_operator != (self.value is None):
            raise ValueError("Null operators omit value; other operators require a value")
        if isinstance(self.value, str):
            if len(self.value) > 500 or any(ord(c) < 32 for c in self.value) or "\\" in self.value:
                raise ValueError("Filter strings must be short, without control characters or backslashes")
        return self


class Metric(Contract):
    operation: Literal["count", "count_distinct", "sum", "avg", "min", "max"]
    field: ColumnName | None = Field(default=None, description="Omit or use null for count (counts rows). Required for other operations. Use inspected column names, not display labels.")

    @model_validator(mode="after")
    def check_field(self):
        if self.operation == "count" and self.field is not None:
            raise ValueError("count counts rows and does not accept a field")
        if self.operation != "count" and self.field is None:
            raise ValueError("This metric requires a field")
        return self


class Order(Contract):
    field: ColumnName
    direction: Literal["asc", "desc"] = "desc"


class TimeBucket(Contract):
    field: ColumnName
    interval: Literal["month", "year"] = "month"


class Query(Contract):
    dataset_id: DatasetId
    columns: list[ColumnName] = Field(default_factory=list, max_length=12)
    filters: list[Filter] = Field(default_factory=list, max_length=12)
    group_by: list[ColumnName] = Field(default_factory=list, max_length=3)
    metric: Metric | None = None
    time_bucket: TimeBucket | None = None
    order_by: Order | None = None
    limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 20

    @model_validator(mode="after")
    def check_shape(self):
        if self.metric is not None and self.columns:
            raise ValueError("Aggregate queries use group_by, not columns")
        if self.metric is None and (self.group_by or self.time_bucket or not self.columns):
            raise ValueError("Row queries require explicit columns and cannot group")
        if len(set(self.columns)) != len(self.columns) or len(set(self.group_by)) != len(self.group_by):
            raise ValueError("Repeated fields are not allowed")
        return self


class RowQuery(Contract):
    """Model-facing individual rows; no aggregate fields."""
    dataset_id: DatasetId
    columns: list[ColumnName] = Field(min_length=1, max_length=12, description="Exact inspected column names, not display labels.")
    filters: list[Filter] = Field(default_factory=list, max_length=12)
    order_by: Order | None = None
    limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 20


class AggregateQuery(Contract):
    """Model-facing summaries; the server owns aliases and sort fields."""
    dataset_id: DatasetId
    group_by: list[ColumnName] = Field(default_factory=list, max_length=3, description="Exact inspected category column names. Empty for a single total. Do not supply columns.")
    metric: Metric
    filters: list[Filter] = Field(default_factory=list, max_length=12)
    time_bucket: TimeBucket | None = None
    sort: Literal['value_desc', 'value_asc', 'period_asc', 'period_desc'] | None = Field(default=None, description="value_desc for top/highest rankings; period_asc for chronological trends. Never supply order_by.")
    limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 20

    def to_query(self) -> Query:
        sort = self.sort or ('period_asc' if self.time_bucket else 'value_desc')
        field, direction = sort.split('_')
        return Query(**self.model_dump(exclude={'sort'}), order_by=Order(field=field, direction=direction))


class AnalysisRequest(Contract):
    dataset_interest: str = Field(min_length=2, max_length=200)
    question: str = Field(min_length=5, max_length=1500)

    @model_validator(mode="after")
    def meaningful(self):
        if not self.dataset_interest.strip() or not self.question.strip():
            raise ValueError("Tell us what data interests you and what you want to learn")
        return self


class Search(Contract):
    text: str = Field(min_length=1, max_length=200)
    limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 10

    @model_validator(mode="after")
    def meaningful_text(self):
        if not self.text.strip():
            raise ValueError("Search text cannot be blank")
        return self
