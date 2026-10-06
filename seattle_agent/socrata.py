"""Generic tools restricted to Seattle's official catalog and data host."""

from datetime import datetime, timezone
import json
import re

import httpx
from pydantic import TypeAdapter

from .models import Column, DatasetId, Query, Schema, Search
from .query import compile_query
from .tools import DataUnavailable

HOST = "data.seattle.gov"
CATALOG = "https://api.us.socrata.com/api/catalog/v1"


def retrieved() -> str:
    return datetime.now(timezone.utc).isoformat()


class SeattleTools:
    def __init__(self, transport=None):
        self.transport = transport

    def _get(self, url, params=None):
        # Hosts/paths come only from server constants and validated IDs.
        try:
            with httpx.Client(timeout=20, follow_redirects=False, transport=self.transport) as client:
                with client.stream('GET', url, params=params) as response:
                    if response.status_code != 200:
                        raise DataUnavailable(f"Seattle/Socrata returned HTTP {response.status_code}. Retry later or check access.")
                    chunks = []; size = 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 1_000_000:
                            raise DataUnavailable("Data response exceeded the 1 MB safety limit. Narrow the request.")
                        chunks.append(chunk)
                    return json.loads(b''.join(chunks))
        except (httpx.HTTPError, ValueError) as exc:
            raise DataUnavailable("Could not read Seattle data. The request timed out, failed, or returned invalid JSON.") from exc

    def search(self, request: Search) -> dict:
        params = {'domains': HOST, 'search_context': HOST, 'provenance': 'official',
                  'q': request.text, 'limit': request.limit}
        response = self._get(CATALOG, params)
        if not isinstance(response, dict) or not isinstance(response.get('results'), list):
            raise DataUnavailable('Catalog returned an incompatible response')
        results = []
        for item in response.get('results', []):
            if not isinstance(item, dict) or not isinstance(item.get('resource'), dict) or not isinstance(item.get('metadata'), dict):
                raise DataUnavailable('Catalog returned invalid asset metadata')
            resource = item.get('resource', {})
            if item.get('metadata', {}).get('domain') != HOST or resource.get('provenance') != 'official':
                continue
            identifier = resource.get('id', '')
            if not isinstance(identifier, str) or not re.fullmatch(r'[a-z0-9]{4}-[a-z0-9]{4}', identifier):
                continue
            supported = resource.get('type') == 'dataset' and resource.get('lens_view_type') == 'tabular'
            results.append({'dataset_id': identifier, 'title': resource.get('name', identifier),
                            'description': (resource.get('description') or '')[:6000],
                            'asset_type': resource.get('type'), 'updated_at': resource.get('data_updated_at'),
                            'supported': supported,
                            'limitation': None if supported else 'Only native tabular datasets are supported; files, maps, and external GIS are not queryable here.',
                            'source_url': f'https://{HOST}/d/{identifier}'})
        return {'datasets': results, 'retrieved_at': retrieved(), 'catalog_url': CATALOG,
                'parameters': params, 'warning': 'Search results are bounded; they are not the whole catalog.'}

    def inspect(self, dataset_id: str) -> Schema:
        identifier = TypeAdapter(DatasetId).validate_python(dataset_id)
        data = self._get(f'https://{HOST}/api/views/{identifier}.json')
        if not isinstance(data, dict) or not isinstance(data.get('columns', []), list):
            raise DataUnavailable('Dataset returned incompatible metadata')
        if data.get('id') != identifier:
            raise DataUnavailable("Dataset metadata identity did not match the request")
        supported = data.get('viewType') == 'tabular' and data.get('displayType') in {'table', 'fatrow'}
        columns = []
        for column in data.get('columns', []):
            if not isinstance(column, dict):
                raise DataUnavailable('Dataset returned invalid column metadata')
            name = column.get('fieldName', '')
            if not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_]*', name):
                continue
            cached = column.get('cachedContents', {})
            columns.append(Column(name=name, label=column.get('name', name), data_type=column.get('dataTypeName', 'unknown'),
                                  description=column.get('description'),
                                  observed_min=str(cached['smallest']) if 'smallest' in cached else None,
                                  observed_max=str(cached['largest']) if 'largest' in cached else None))
        return Schema(dataset_id=identifier, title=data.get('name', identifier),
                      description=(data.get('description') or '')[:12000], asset_type='dataset' if supported else data.get('viewType', 'unsupported'),
                      columns=columns, updated_at=datetime.fromtimestamp(data['rowsUpdatedAt'], timezone.utc) if data.get('rowsUpdatedAt') else None,
                      row_definition=None,
                      coverage_notes='Column min/max values are cached observations, not proof of continuous coverage or complete years. Row definition must be established from descriptions and identifiers before interpreting counts.')

    def query(self, request: Query) -> dict:
        schema = self.inspect(request.dataset_id)  # Fresh inspection prevents stale/fabricated fields.
        parameters = compile_query(request, schema)
        url = f'https://{HOST}/resource/{request.dataset_id}.json'
        rows = self._get(url, parameters)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise DataUnavailable("Seattle did not return a tabular result")
        if len(rows) > request.limit + 1:
            raise DataUnavailable("Seattle ignored the requested output bound")
        truncated = len(rows) > request.limit
        return {'dataset_id': request.dataset_id, 'title': schema.title, 'rows': rows[:request.limit],
                'source_url': f'https://{HOST}/d/{request.dataset_id}', 'query_url': url,
                'query': request.model_dump(mode='json'), 'parameters': parameters, 'retrieved_at': retrieved(),
                'truncated': truncated, 'row_definition': schema.row_definition,
                'description': schema.description, 'coverage_notes': schema.coverage_notes,
                'warnings': [*(['More results exist; the table/chart is truncated.'] if truncated else []),
                             'Counts count dataset rows unless explicitly counting a distinct identifier; they are not population-adjusted rates.',
                             'Missing periods are not zero. Current and boundary periods may be incomplete.']}
