# Test and review the query foundation on Windows

This branch contains a Python backend foundation, not the customer website.
There is no question box, live dataset discovery, or OpenAI integration yet.
The interactive FastAPI documentation lets you inspect the backend contracts.
No API key is needed for this stage.

## 1. Get the review branch

If you already cloned the project, run from its folder in PowerShell:

```powershell
git status
git fetch origin
git switch --track origin/review/query-foundation
```

Keep any local work before switching. If you already have the review branch,
use `git switch review/query-foundation` instead of creating it again.

For a new checkout:

```powershell
git clone --branch review/query-foundation https://github.com/notpoa/seattle-data-agent.git
cd seattle-data-agent
code .
```

## 2. Install and test

Install Python 3.12, then use the VS Code PowerShell terminal in the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -v
```

Expected: no broken requirements and 43 passing tests. A dependency may emit a
deprecation warning for the HTTP test client. Windows CI is configured; local
development validation was performed on Linux, not a Windows machine.

Tests cover grouped row counts with a date window, numeric aggregates, literal
escaping, invalid fields and types, unsupported assets, row limits, API error
responses, and offline CLI compilation. The fixtures are synthetic test inputs,
not Seattle facts or live data.

## 3. Start the backend

```powershell
.\.venv\Scripts\python.exe -m uvicorn seattle_agent.api:app --reload --port 8000
```

Leave this terminal running. In your own local browser, open
`http://127.0.0.1:8000/docs`. This is the interactive API documentation, not the
planned customer website. The root route `/` is not implemented and returns 404.

Use **Try it out**, then **Execute** on these routes:

| Route | Input | Expected result |
| --- | --- | --- |
| `GET /health` | None | 200, `status: ok`, `live_data_enabled: false`, `agent_enabled: false` |
| `POST /api/datasets/search` | `{"text":"trees","limit":5}` | 503 with an explanation that live integration is unavailable |
| `GET /api/datasets/{dataset_id}` | `abcd-1234` (synthetic format example) | 503; no fabricated schema |
| `POST /api/query` | `{"dataset_id":"abcd-1234","columns":["area"],"limit":101}` | 422; maximum output limit is 100 |
| `POST /api/query` | `{"dataset_id":"abcd-1234","sql":"SELECT *"}` | 422; unrestricted SQL is not accepted |

The synthetic ID is only for exercising input validation. It is not a discovered
Seattle dataset. A valid-shaped query still returns 503 until the real data
transport is implemented. These expected errors demonstrate honest API behavior;
they do not demonstrate successful data retrieval.

In a second PowerShell terminal, health and CLI checks are also available:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
.\.venv\Scripts\python.exe -m seattle_agent.cli --help
.\.venv\Scripts\python.exe -m seattle_agent.cli search "trees"
```

The last command reports unavailable data and exits with code 1. Stop the server
with Ctrl+C in its terminal.

## 4. See the offline query compiler work

This test exercises a count grouped by area over the complete 2025 calendar year
using synthetic schema inputs. It verifies the exact compiled parameters:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_query.py::test_grouped_ranking_with_explicit_time_window -v
.\.venv\Scripts\python.exe -m pytest tests/test_api_cli.py::test_offline_cli_compiles_and_labels_output -v
```

Read `seattle_agent/models.py` for allowed query arguments and
`seattle_agent/query.py` for schema checks and parameter compilation. Read
`tests/test_query.py` to see accepted and rejected examples. Information flows
from a validated request through schema checks to bounded parameters. The next
connector will send those parameters to Seattle only after API syntax has been
verified against current official documentation.

## 5. Review changes on GitHub

Select `review/query-foundation` in GitHub's branch dropdown. The changes are on
that branch, so `main` will still show the original README. The Actions tab shows
the configured Linux/Windows checks once GitHub runs them. A local passing run
does not establish that hosted CI has passed.

The next stage completes live discovery, schema inspection, and bounded querying.
Cloud network access to the official docs and Seattle endpoints must work first;
see `INTEGRATION.md`. Running this foundation locally does not enable the missing
connector by itself. Then the OpenAI loop and Next.js interface can be built.
