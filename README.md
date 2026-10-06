# Seattle Data Agent

A website in development for answering Seattle questions by discovering relevant
datasets in Seattle's official Open Data catalog, inspecting their meaning and
schema, running bounded queries, and explaining results with sources.

## Actual starting point and current status

The inspected checkout at `73620cc` contained only a one-line README. It did not
contain the expected starter, source files, tests, CLI, or planning documents.
This first stage builds an **offline query foundation**, not a live data agent.

Implemented:

- Structured, strict query contracts shared by FastAPI, CLI, and future LLM tools.
- Schema-based validation of identifiers, types, filters, aggregate fields, and sorting.
- Bounded row selection and row counts, numeric aggregates, and grouped rankings.
- No arbitrary SQL, Python execution, caller-supplied URLs, or dataset allowlist.
- FastAPI request validation, explicit unavailable responses, and a local CLI.
- Automated tests and GitHub Actions for Python 3.12 on Linux and Windows.
- Render backend configuration (prepared only; nothing deployed).

**Not implemented yet:** live catalog search, upstream schema inspection/querying,
result provenance and truncation handling, OpenAI loop, percentages/trends,
multiple-dataset compatibility checks, Next.js website, charts, and Vercel setup.
The compiler requests one extra row to enable future truncation detection; it
does not itself fetch or trim results.

Live API documentation and data access returned proxy 403 in this workspace.
Integration implementation is deferred until current official documentation can
be read and real Seattle requests tested. There are no simulated live results.
`/health` confirms server health and explicitly reports that data and agent
capabilities are disabled. All data routes currently return HTTP 503.

## Run locally in Windows / VS Code

VS Code now includes setup, test, run, and debug controls. See
[the VS Code walkthrough](docs/REVIEW.md#vs-code-buttons-recommended) for the
recommended way to start the project without entering each install command.

Install Python 3.12. Open the repository folder in VS Code, then open a PowerShell
terminal. These commands use the virtual environment directly, so changing
PowerShell's script execution policy is unnecessary.

```powershell
cd C:\path\to\seattle-data-agent
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn seattle_agent.api:app --reload --port 8000
```

In another PowerShell terminal:

```powershell
cd C:\path\to\seattle-data-agent
Invoke-RestMethod http://127.0.0.1:8000/health
$body = @{ text = "trees"; limit = 5 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/datasets/search -ContentType "application/json" -Body $body
.\.venv\Scripts\python.exe -m seattle_agent.cli search "trees"
```

The health request succeeds. The search request intentionally reports a real
unavailable error (PowerShell displays HTTP 503); the CLI exits with code 1.
FastAPI's generated API documentation is at `/docs` on your local server.
Press Ctrl+C in the server terminal to stop it.

On Linux/macOS use `python3 -m venv .venv`, then `.venv/bin/python` in place of
`.\.venv\Scripts\python.exe` in the same commands.

## How this stage works

An HTTP request or CLI JSON file becomes a validated `Query`. Only known
operations are allowed. The compiler then checks the query against a supplied
`Schema`, rejecting unknown fields, wrong types, and unsupported assets. It
produces bounded query parameters rather than accepting executable model text.
The query syntax is a provisional offline contract; official API verification
remains required before connecting it to a real endpoint.

For example, a count means **rows**, not automatically people, incidents, reports,
or offenses. Schema contracts store row definition and coverage as unknown when
there is no evidence. Query arguments can express a date window, but the compiler
does not determine completeness, choose a correct denominator, or justify a
comparison. Those require inspected dataset documentation and analysis logic.

The API depends on a `DataTools` interface. Test-only implementations exercise
the boundary without network access. The production implementation explicitly
fails until real integration is enabled. Tests never serve example data in the
application.

## Environment variables and credentials

This stage requires no credentials or application environment variables.
Render supplies `PORT`; `render.yaml` specifies the Python version. Never put
credentials in source control or frontend variables. `.env` files are ignored.

The next AI stage will read an OpenAI API key **only in the backend**, select a
tool-calling model with a backend model setting, and fail clearly if configuration
is missing. Those settings are not implemented yet. Do not supply secret values
in chat. Cloud proxy secret targets reserve the `OPENAI_` prefix; a future cloud
binding must use a permitted backend name and explicit HTTPS destination.

## Network access needed to finish stage 1

Allow these domains in the cloud environment settings:

- `dev.socrata.com`: current official discovery, metadata, and query documentation.
- `api.us.socrata.com`: the catalog API, restricted to Seattle through domain filters.
- `data.seattle.gov`: official dataset metadata, data, and source pages.

These additions were saved in an environment draft; a saved draft does not change
runtime access or publish the environment. Review/save the settings and publish
when required by the onboarding UI. Then resume official documentation checks,
live discovery, metadata normalization, and bounded query validation.

## Deployment preparation

`render.yaml` prepares a Python backend service with `/health` as its health
check. It currently serves only the foundation API; healthy does not mean live
analysis works. The build installs pinned dependencies and the package. The
start command binds to Render's `PORT`. No deployment has
been performed. Complete live data and agent validation before deploying for
customers. The frontend and Vercel configuration will be added in stage 3.

See [the milestone plan](docs/PLAN.md) and [integration verification checklist](docs/INTEGRATION.md).

For a step-by-step review on Windows, see [testing this stage](docs/REVIEW.md).
