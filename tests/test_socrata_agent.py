import json

import httpx
import pytest

from seattle_agent.agent import analyze
from seattle_agent.models import AnalysisRequest, Query, Search
from seattle_agent.query import QueryError, compile_query
from seattle_agent.socrata import SeattleTools
from seattle_agent.tools import DataUnavailable


def catalog_item(identifier='abcd-1234', domain='data.seattle.gov', provenance='official', asset='dataset'):
    return {'metadata': {'domain': domain}, 'resource': {'id': identifier, 'name': 'Synthetic fixture',
            'description': 'One synthetic record', 'provenance': provenance, 'type': asset, 'lens_view_type': 'tabular'}}


def test_discovery_enforces_domain_and_provenance_and_does_not_hide_unsupported():
    def handler(request):
        assert request.url.host == 'api.us.socrata.com'
        assert request.url.params['domains'] == 'data.seattle.gov'
        assert request.url.params['q'] == 'trees'
        return httpx.Response(200, json={'results': [catalog_item(), catalog_item('zzzz-0000', domain='evil.example'),
            catalog_item('yyyy-0000', provenance='community'), catalog_item('xxxx-0000', asset='file')]})
    output = SeattleTools(httpx.MockTransport(handler)).search(Search(text='trees'))
    assert [d['dataset_id'] for d in output['datasets']] == ['abcd-1234', 'xxxx-0000']
    assert output['datasets'][1]['supported'] is False


def test_query_reinspects_schema_and_detects_truncation():
    paths = []
    def handler(request):
        paths.append(request.url.path)
        if '/api/views/' in request.url.path:
            return httpx.Response(200, json={'id': 'abcd-1234', 'viewType': 'tabular', 'displayType': 'table',
                'columns': [{'fieldName': 'area', 'name': 'Area', 'dataTypeName': 'text'}]})
        assert request.url.params['$limit'] == '3'
        return httpx.Response(200, json=[{'area': 'A'}, {'area': 'B'}, {'area': 'C'}])
    result = SeattleTools(httpx.MockTransport(handler)).query(Query(dataset_id='abcd-1234', columns=['area'], limit=2))
    assert paths == ['/api/views/abcd-1234.json', '/resource/abcd-1234.json']
    assert result['rows'] == [{'area': 'A'}, {'area': 'B'}]
    assert result['truncated'] is True and result['retrieved_at'] and result['parameters']
    assert result['source_url'] == 'https://data.seattle.gov/d/abcd-1234'


@pytest.mark.parametrize('status', [302, 403, 429, 500])
def test_upstream_failures_and_redirects_not_followed(status):
    tools = SeattleTools(httpx.MockTransport(lambda r: httpx.Response(status, headers={'Location': 'https://evil.example'})))
    with pytest.raises(DataUnavailable, match=f'HTTP {status}'):
        tools.search(Search(text='trees'))


def test_response_byte_limit():
    tools = SeattleTools(httpx.MockTransport(lambda r: httpx.Response(200, content=b' ' * 1_000_001)))
    with pytest.raises(DataUnavailable, match='1 MB'):
        tools.search(Search(text='trees'))


def test_monthly_trends_require_window_and_compile_correctly(schema):
    args = {'dataset_id': schema.dataset_id, 'metric': {'operation': 'count'},
            'time_bucket': {'field': 'recorded_at', 'interval': 'month'}}
    with pytest.raises(QueryError, match='explicit start'):
        compile_query(Query(**args), schema)
    result = compile_query(Query(**args, filters=[{'field': 'recorded_at', 'operator': 'gte', 'value': '2025-01-01'},
        {'field': 'recorded_at', 'operator': 'lt', 'value': '2026-01-01'}]), schema)
    assert result['$select'] == 'date_trunc_ym(recorded_at) AS period, count(*) AS value'
    assert result['$group'] == 'date_trunc_ym(recorded_at)'
    assert result['$order'] == 'period ASC'


def call(name, args):
    return {'role': 'assistant', 'content': None, 'tool_calls': [{'id': 'test-call', 'type': 'function',
            'function': {'name': name, 'arguments': json.dumps(args)}}]}


class FakeTools:
    def __init__(self, schema): self.schema = schema; self.queries = 0
    def search(self, request): return {'datasets': [{'dataset_id': self.schema.dataset_id, 'title': 'Synthetic fixture'}]}
    def inspect(self, identifier): return self.schema
    def query(self, request):
        self.queries += 1
        return {'rows': [{'value': '5'}], 'dataset_id': request.dataset_id}


def test_agent_inspects_before_query_and_returns_only_tool_results(schema):
    tools = FakeTools(schema)
    script = iter([call('inspect', {'dataset_id': schema.dataset_id}),
        call('aggregate', {'dataset_id': schema.dataset_id, 'metric': {'operation': 'count'}}),
        call('finish', {'status': 'answered', 'message': 'There are 5 synthetic rows.'})])
    events = list(analyze(AnalysisRequest(dataset_interest='synthetic', question='Count records'), tools,
                         model_call=lambda messages, specs: next(script)))
    assert tools.queries == 1
    assert next(e for e in events if e['type'] == 'result')['result']['rows'] == [{'value': '5'}]
    assert events[-1]['status'] == 'answered'


def test_agent_rejects_fabricated_id_and_uninspected_query(schema):
    tools = FakeTools(schema)
    script = iter([call('inspect', {'dataset_id': 'zzzz-0000'}),
        call('aggregate', {'dataset_id': schema.dataset_id, 'metric': {'operation': 'count'}}),
        call('finish', {'status': 'clarification', 'message': 'Please clarify the record definition.'})])
    events = list(analyze(AnalysisRequest(dataset_interest='synthetic', question='Count records'), tools,
                         model_call=lambda messages, specs: next(script)))
    assert tools.queries == 0
    assert len([e for e in events if e['type'] == 'warning']) == 2


def test_missing_key_returns_real_discovery_then_configuration_error(schema, monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('SEATTLE_OPENAI_API_KEY', raising=False)
    events = list(analyze(AnalysisRequest(dataset_interest='synthetic', question='Count records'), FakeTools(schema)))
    assert events[1]['type'] == 'datasets'
    assert events[-1]['type'] == 'error' and 'SEATTLE_OPENAI_API_KEY' in events[-1]['message']
    assert not any(e['type'] == 'answer' for e in events)


def test_successful_finish_without_query_rejected(schema):
    script = iter([call('finish', {'status': 'answered', 'message': 'Invented numbers'}),
        call('finish', {'status': 'clarification', 'message': 'Which time period?'})])
    events = list(analyze(AnalysisRequest(dataset_interest='synthetic', question='Count records'), FakeTools(schema),
                         model_call=lambda messages, specs: next(script)))
    assert any(e['type'] == 'warning' and 'No successful' in e['message'] for e in events)
    assert events[-1]['status'] == 'clarification'


def test_agent_budget_exhaustion_is_explicit(schema):
    events = list(analyze(AnalysisRequest(dataset_interest='synthetic', question='Count records'), FakeTools(schema),
                         model_call=lambda messages, specs: call('inspect', {'dataset_id': schema.dataset_id})))
    assert events[-1]['type'] == 'error' and 'limit' in events[-1]['message']
    assert not any(e['type'] == 'answer' for e in events)


def test_tool_failure_has_no_fabricated_result(schema):
    class FailingTools(FakeTools):
        def query(self, request): raise DataUnavailable('Seattle returned HTTP 429')
    script = iter([call('inspect', {'dataset_id': schema.dataset_id}),
        call('aggregate', {'dataset_id': schema.dataset_id, 'metric': {'operation': 'count'}}),
        call('finish', {'status': 'unsupported', 'message': 'The service is rate limited. Retry later.'})])
    events = list(analyze(AnalysisRequest(dataset_interest='synthetic', question='Count records'), FailingTools(schema),
                         model_call=lambda messages, specs: next(script)))
    assert any(e['type'] == 'warning' and '429' in e['message'] for e in events)
    assert not any(e['type'] == 'result' for e in events)


def test_distinct_counts_require_known_identifiers(schema):
    result = compile_query(Query(dataset_id=schema.dataset_id, metric={'operation': 'count_distinct', 'field': 'area'}), schema)
    assert result['$select'] == 'count(distinct area) AS value'
    with pytest.raises(QueryError, match='inspected schema'):
        compile_query(Query(dataset_id=schema.dataset_id, metric={'operation': 'count_distinct', 'field': 'invented'}), schema)


def test_trend_window_order_is_validated(schema):
    with pytest.raises(QueryError):
        compile_query(Query(dataset_id=schema.dataset_id, metric={'operation': 'count'}, time_bucket={'field': 'recorded_at'},
            filters=[{'field': 'recorded_at', 'operator': 'gte', 'value': '2026-01-01'},
                     {'field': 'recorded_at', 'operator': 'lt', 'value': '2025-01-01'}]), schema)


def test_empty_initial_search_can_be_rephrased_by_agent(schema):
    class SearchTools(FakeTools):
        def search(self, request):
            if request.text == 'vague original phrase': return {'datasets': []}
            return super().search(request)
    script = iter([call('search', {'text': 'better search terms'}),
        call('inspect', {'dataset_id': schema.dataset_id}),
        call('finish', {'status': 'clarification', 'message': 'Which year should I use?'})])
    events = list(analyze(AnalysisRequest(dataset_interest='vague original phrase', question='Count records'), SearchTools(schema),
                         model_call=lambda messages, specs: next(script)))
    assert any(e['type'] == 'selected' for e in events)
    assert events[-1]['status'] == 'clarification'
