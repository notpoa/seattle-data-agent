import pytest

from seattle_agent.models import Column, Schema


@pytest.fixture
def schema():
    # Entirely synthetic. These identifiers and rows are never used by the app.
    return Schema(
        dataset_id="abcd-1234", title="Synthetic test records", description="Test fixture only",
        asset_type="dataset", row_definition="One synthetic measurement",
        columns=[
            Column(name="area", label="Area", data_type="text"),
            Column(name="amount", label="Amount", data_type="number"),
            Column(name="recorded_at", label="Recorded at", data_type="floating_timestamp"),
            Column(name="active", label="Active", data_type="checkbox"),
            Column(name="shape", label="Shape", data_type="point"),
        ],
    )
