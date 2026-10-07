import json

import httpx
import pytest
from pydantic import ValidationError

from seattle_agent.agent import SPECS, analyze
from seattle_agent.models import AggregateQuery, AnalysisRequest, RowQuery
from seattle_agent.socrata import SeattleTools


def test_model_tools_separate_projection_from_aggregation():
    specs = {s['function']['name']: s['function']['parameters'] for s in SPECS}
    assert 'columns' not in specs['aggregate']['properties']
    assert 'order_by' not in specs['aggregate']['properties']
    assert 'metric' in specs['aggregate']['required']
    assert 'metric' not in specs['query']['properties']
    assert 'columns' in specs['query']['required']
    with pytest.raises(ValidationError):
        RowQuery(dataset_id='abcd-1234', columns=['type'], metric={'operation': 'count'})
    with pytest.raises(ValidationError):
        AggregateQuery(dataset_id='abcd-1234', metric={'operation': 'count'}, columns=['type'])


def test_server_owns_sort_alias_for_rankings_and_trends():
    ranking = AggregateQuery(dataset_id='abcd-1234', metric={'operation': 'count'}, group_by=['type'], limit=5).to_query()
    assert not ranking.columns
    assert ranking.order_by.field == 'value' and ranking.order_by.direction == 'desc'
    trend = AggregateQuery(dataset_id='abcd-1234', metric={'operation': 'count'}, time_bucket={'field': 'issueddate'}).to_query()
    assert trend.order_by.field == 'period' and trend.order_by.direction == 'asc'


def test_permit_ranking_repairs_mixed_arguments_then_executes_valid_aggregate():
    executed = []
    def upstream(request):
        if 'catalog/v1' in request.url.path:
            return httpx.Response(200, json={'results': [{'metadata': {'domain': 'data.seattle.gov'},
                'resource': {'id': 'abcd-1234', 'name': 'Synthetic permits', 'provenance': 'official',
                             'type': 'dataset', 'lens_view_type': 'tabular'}}]})
        if 'api/views' in request.url.path:
            return httpx.Response(200, json={'id': 'abcd-1234', 'name': 'Synthetic permits',
                'viewType': 'tabular', 'displayType': 'table', 'description': 'Synthetic permit rows only.',
                'columns': [{'fieldName': 'permittypemapped', 'name': 'PermitTypeMapped', 'dataTypeName': 'text'},
                            {'fieldName': 'issueddate', 'name': 'IssuedDate', 'dataTypeName': 'calendar_date'}]})
        executed.append(dict(request.url.params))
        return httpx.Response(200, json=[{'permittypemapped': 'Building', 'value': '5'}])
    ranking = {'dataset_id': 'abcd-1234', 'group_by': ['permittypemapped'], 'metric': {'operation': 'count'},
               'filters': [{'field': 'issueddate', 'operator': 'gte', 'value': '2025-01-01'},
                           {'field': 'issueddate', 'operator': 'lt', 'value': '2026-01-01'}],
               'sort': 'value_desc', 'limit': 5}
    script = iter([
        ('inspect', {'dataset_id': 'abcd-1234'}),
        ('aggregate', {**ranking, 'columns': ['permittypemapped'], 'order_by': {'field': 'count'}}),
        ('aggregate', ranking),
        ('finish', {'status': 'answered', 'message': 'There are 5 synthetic Building rows issued in 2025.'}),
    ])
    def model(messages, specs):
        name, args = next(script)
        return {'role': 'assistant', 'content': None, 'tool_calls': [
            {'id': 'synthetic-call', 'function': {'name': name, 'arguments': json.dumps(args)}}]}
    events = list(analyze(AnalysisRequest(dataset_interest='building permits', question='Rank up to five permit types issued in 2025.'),
                          SeattleTools(httpx.MockTransport(upstream)), model))
    assert len(executed) == 1
    assert executed[0] == {'$select': 'permittypemapped, count(*) AS value', '$group': 'permittypemapped',
        '$where': "issueddate >= '2025-01-01' AND issueddate < '2026-01-01'", '$order': 'value DESC', '$limit': '6'}
    assert any(e['type'] == 'warning' for e in events)
    assert events[-1]['status'] == 'answered'
    result = next(e['result'] for e in events if e['type'] == 'result')
    assert result['rows'] == [{'permittypemapped': 'Building', 'value': '5'}]
