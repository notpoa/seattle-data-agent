"""Data-tool interface, shared errors, and an explicitly disabled adapter.

The normal API uses SeattleTools. A disabled adapter fails without sample data.
"""

from typing import Protocol

from .models import Query, Schema, Search


class DataUnavailable(RuntimeError):
    pass


class DataTools(Protocol):
    def search(self, request: Search) -> dict: ...
    def inspect(self, dataset_id: str) -> Schema: ...
    def query(self, request: Query) -> dict: ...


class PendingSeattleTools:
    def _unavailable(self):
        raise DataUnavailable(
            "Live Seattle data is not enabled for this application instance. "
            "Configure a data provider before using these routes."
        )

    def search(self, request: Search) -> dict:
        return self._unavailable()

    def inspect(self, dataset_id: str) -> Schema:
        return self._unavailable()

    def query(self, request: Query) -> dict:
        return self._unavailable()
