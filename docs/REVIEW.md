# Review the simple Seattle website

Use the setup and run tasks in the [README](../README.md). Open the local website
at port 8000's root `/`, not `/docs`. It asks for a dataset/topic and your question.

## Review without a model key

Submit a topic such as "SPD arrests" and a question such as "Show monthly report
counts in 2025". The page should show real catalog candidates followed by an
explicit missing-OpenAI-configuration error. This tests browser-to-backend-to-
catalog discovery, not successful analysis. No mock results are served.

## Review with a backend key

Create `.env` locally from `.env.example` if one does not already exist. Enter the
key securely in that local file, restart the backend, and submit a dated question.
Expect progress as datasets are inspected, then actual tables and an explanation
or a clarification. Check official sources, query details, retrieval timestamps,
row definitions, and warnings. A trend chart appears only for suitable, complete
returned series; chart visibility does not establish source-data completeness.

Cross-dataset correlations are not supported yet. The model should explain that
limitation rather than asserting a correlation. Unsupported assets and upstream
failures should also remain explicit.

## Troubleshooting Windows setup

| Symptom | Action |
| --- | --- |
| `py` missing | Install Python 3.12 with the Windows launcher and restart VS Code. |
| `npm` missing | Install Node.js LTS and restart VS Code. |
| `uvicorn` or `dotenv` missing | Run **Seattle: Set up Python environment** again. |
| Root page says website not built | Run **Seattle: Set up website**, then restart the backend. |
| Old page after an update | Rebuild the website, restart the backend, and refresh the browser. |
| Port 8000 is in use | Stop the old backend/debug task before starting another. |
| AI configuration error | Put the key in the backend `.env` and restart; never use frontend settings. |
| OpenAI HTTP 401/403/429 | Check key validity, model access, API billing/quota, and retry after resolving the cause. |
| Socrata HTTP 429 or timeout | Narrow your question and retry later; no results are fabricated. |

## Backend contracts

`/docs` remains the developer API explorer. `/health` reports configured
capabilities, not proof of upstream access or valid credentials. `/api/analyze`
streams progress/evidence/error events. `/api/datasets/search`,
`/api/datasets/{id}`, and `/api/query` are the reusable data-tool endpoints.

The CLI can search and inspect independently of the model:

```powershell
.\.venv\Scripts\python.exe -m seattle_agent.cli search "building permits"
```

Only use dataset IDs returned by actual discovery; do not copy synthetic test IDs
as live sources. The GitHub review branch is `review/query-foundation`.
