import json

from fastapi.testclient import TestClient

from seattle_agent.api import create_app
from seattle_agent.cli import main
from seattle_agent.models import Query
from seattle_agent.query import compile_query
from seattle_agent.tools import PendingSeattleTools


def test_server_health_is_not_claim_of_data_readiness(monkeypatch):
    monkeypatch.setattr('seattle_agent.api.api_key', lambda: None)
    with TestClient(create_app()) as client:
        result = client.get("/health")
        assert result.status_code == 200
        assert result.json()["live_data_enabled"] is True
        assert result.json()["agent_enabled"] is False
        assert 'not live upstream connectivity' in result.json()['note']


def test_live_routes_fail_honestly():
    with TestClient(create_app(PendingSeattleTools())) as client:
        responses = [client.post("/api/datasets/search", json={"text": "trees"}),
                     client.get("/api/datasets/abcd-1234"),
                     client.post("/api/query", json={"dataset_id": "abcd-1234", "columns": ["area"]})]
        for response in responses:
            assert response.status_code == 503
            assert response.json()["error"] == "data_unavailable"
            assert "not enabled" in response.json()["detail"]


def test_bad_arguments_fail_before_tools():
    with TestClient(create_app()) as client:
        assert client.get("/api/datasets/not-an-id").status_code == 422
        assert client.post("/api/query", json={"dataset_id": "abcd-1234", "sql": "SELECT *"}).status_code == 422
        assert client.post("/api/datasets/search", json={"text": "trees", "domain": "evil.example"}).status_code == 422


def test_api_passes_validated_arguments_to_transport(schema):
    class SyntheticTestTools:
        def search(self, request):
            return {"test_only": True, "search_text": request.text}

        def inspect(self, dataset_id):
            assert dataset_id == schema.dataset_id
            return schema

        def query(self, request):
            assert isinstance(request, Query)
            return {"test_only": True, "parameters": compile_query(request, schema)}

    with TestClient(create_app(SyntheticTestTools())) as client:
        assert client.post("/api/datasets/search", json={"text": "trees"}).json()["search_text"] == "trees"
        assert client.get("/api/datasets/abcd-1234").json()["row_definition"] == "One synthetic measurement"
        response = client.post("/api/query", json={"dataset_id": "abcd-1234", "metric": {"operation": "count"}})
        assert response.status_code == 200
        assert response.json()["parameters"]["$select"] == "count(*) AS value"
        response = client.post("/api/query", json={"dataset_id": "abcd-1234", "columns": ["invented"]})
        assert response.status_code == 422
        assert response.json()["error"] == "invalid_query"


def test_cli_reports_unavailable_to_stderr(capsys, monkeypatch):
    monkeypatch.setattr('seattle_agent.cli.SeattleTools', PendingSeattleTools)
    assert main(["search", "trees"]) == 1
    output = capsys.readouterr()
    assert not output.out
    assert "not enabled" in json.loads(output.err)["error"]


def test_offline_cli_compiles_and_labels_output(tmp_path, schema, capsys):
    request_file = tmp_path / "request.json"
    schema_file = tmp_path / "schema.json"
    request_file.write_text(json.dumps({"dataset_id": "abcd-1234", "metric": {"operation": "count"}}))
    schema_file.write_text(schema.model_dump_json())
    assert main(["compile", str(request_file), str(schema_file)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {"offline_only": True, "parameters": {"$select": "count(*) AS value", "$limit": "21"}}


def test_cli_missing_file_is_controlled_error(capsys):
    assert main(["query", "file-that-does-not-exist.json"]) == 1
    assert "error" in json.loads(capsys.readouterr().err)
