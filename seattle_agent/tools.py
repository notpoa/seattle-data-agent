"""Replaceable transport boundary for real Seattle data tools.

The production transport stays unavailable until official API documentation
and live catalog/schema/query checks can be completed. Tests inject a fake;
the API never substitutes fake or cached example results.
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
            "Live Seattle integration is not enabled. Official Socrata documentation "
            "and Seattle catalog access were blocked by the environment proxy (403). "
            "Allow dev.socrata.com, api.us.socrata.com, and data.seattle.gov in "
            "environment settings, then complete documentation and live integration checks."
        )

    def search(self, request: Search) -> dict:
        return self._unavailable()

    def inspect(self, dataset_id: str) -> Schema:
        return self._unavailable()

    def query(self, request: Query) -> dict:
        return self._unavailable()
