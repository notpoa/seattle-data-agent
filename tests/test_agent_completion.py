import json

from seattle_agent.agent import Budget, analyze
from seattle_agent.models import AnalysisRequest
from seattle_agent.query import QueryError


class CountingTools:
    def __init__(self, schema):
        self.schema = schema
        self.inspections = 0
        self.queries = 0

    def search(self, request):
        return {'datasets': [{'dataset_id': self.schema.dataset_id, 'title': self.schema.title}]}

    def inspect(self, identifier):
        self.inspections += 1
        return self.schema

    def query(self, request):
        self.queries += 1
        if request.columns == ['invented']:
            raise QueryError('Field was not present in the inspected schema')
        return {'dataset_id': request.dataset_id, 'rows': [{'value': '5'}]}


def tool(name, args):
    return {'role': 'assistant', 'content': None, 'tool_calls': [
        {'id': 'test-id', 'function': {'name': name, 'arguments': json.dumps(args)}}]}


def question():
    return AnalysisRequest(dataset_interest='building permits', question='Which five permit types have the most dataset rows in 2025? Inspect the schema and explain which date field you use. Ask me if the choice is ambiguous.')


def test_schema_overview_finishes_without_unnecessary_query(schema):
    data = CountingTools(schema)
    responses = iter([tool('inspect', {'dataset_id': schema.dataset_id}),
                      tool('finish', {'status': 'overview', 'message': 'A synthetic measurement per row.'})])
    events = list(analyze(question(), data, lambda messages, specs: next(responses)))
    assert events[-1]['status'] == 'overview'
    assert data.queries == 0


def test_reserved_turn_finishes_and_identical_queries_execute_once(schema):
    data = CountingTools(schema)
    responses = iter([tool('inspect', {'dataset_id': schema.dataset_id}),
                      tool('aggregate', {'dataset_id': schema.dataset_id, 'metric': {'operation': 'count'}}),
                      tool('aggregate', {'dataset_id': schema.dataset_id, 'metric': {'operation': 'count'}})])
    def model(messages, specs):
        if len(specs) == 1:
            assert specs[0]['function']['name'] == 'finish'
            return tool('finish', {'status': 'answered', 'message': 'There are 5 synthetic records.'})
        return next(responses)
    events = list(analyze(question(), data, model, budget=Budget(max_steps=4)))
    assert events[-1]['status'] == 'answered'
    assert data.queries == 1
    assert len([e for e in events if e['type'] == 'result']) == 1
    assert events[-1]['diagnostics']['model_steps'] == 4


def test_repeated_inspections_do_not_fetch_upstream_again(schema):
    data = CountingTools(schema)
    def model(messages, specs):
        if len(specs) == 1:
            return tool('finish', {'status': 'clarification', 'message': 'Should I use application or issue dates?'})
        return tool('inspect', {'dataset_id': schema.dataset_id})
    events = list(analyze(question(), data, model))
    assert data.inspections == 1
    assert data.queries == 0
    assert events[-1]['status'] == 'clarification'
    assert events[-1]['diagnostics']['model_steps'] == 5


def test_repeated_failed_queries_stop_and_explain_without_fabricated_result(schema):
    data = CountingTools(schema)
    def model(messages, specs):
        if len(specs) == 1:
            return tool('finish', {'status': 'clarification', 'message': 'The requested field is missing. Which category should I use?'})
        if not data.inspections:
            return tool('inspect', {'dataset_id': schema.dataset_id})
        return tool('query', {'dataset_id': schema.dataset_id, 'columns': ['invented']})
    events = list(analyze(question(), data, model))
    assert data.queries == 1
    assert not any(e['type'] == 'result' for e in events)
    assert events[-1]['status'] == 'clarification'
    assert 'inspected schema' in events[-1]['diagnostics']['last_tool_error']


def test_time_exhaustion_is_distinct_from_step_exhaustion(schema):
    ticks = iter([0, 0, 0, 241])
    events = list(analyze(question(), CountingTools(schema),
        lambda messages, specs: tool('inspect', {'dataset_id': schema.dataset_id}), clock=lambda: next(ticks)))
    assert events[-1]['type'] == 'error'
    assert events[-1]['diagnostics']['reason'] == 'time'
    assert events[-1]['diagnostics']['model_steps'] == 1


def test_overview_cannot_bypass_inspection(schema):
    responses = iter([tool('finish', {'status': 'overview', 'message': 'An invented definition.'}),
                      tool('finish', {'status': 'clarification', 'message': 'Which dataset?'})])
    events = list(analyze(question(), CountingTools(schema), lambda messages, specs: next(responses)))
    assert any(e['type'] == 'warning' and 'Inspect' in e['message'] for e in events)
    assert events[-1]['status'] == 'clarification'


def test_analysis_longer_than_old_eight_steps_can_finish(schema):
    responses = iter([tool('inspect', {'dataset_id': schema.dataset_id}), *[
        tool('aggregate', {'dataset_id': schema.dataset_id, 'metric': {'operation': 'count'}, 'limit': n})
        for n in range(1, 10)], tool('finish', {'status': 'answered', 'message': 'Synthetic analysis completed.'})])
    events = list(analyze(question(), CountingTools(schema), lambda messages, specs: next(responses)))
    assert events[-1]['status'] == 'answered'
    assert events[-1]['diagnostics']['model_steps'] == 11


def test_failed_prerequisite_can_be_repaired_before_repeating_query(schema):
    data = CountingTools(schema)
    query = {'dataset_id': schema.dataset_id, 'metric': {'operation': 'count'}}
    responses = iter([tool('aggregate', query), tool('inspect', {'dataset_id': schema.dataset_id}),
                      tool('aggregate', query), tool('finish', {'status': 'answered', 'message': '5 synthetic rows.'})])
    events = list(analyze(question(), data, lambda messages, specs: next(responses)))
    assert data.queries == 1
    assert events[-1]['status'] == 'answered'
