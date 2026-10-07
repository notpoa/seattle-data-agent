# Seattle Data Agent

A simple website with two questions: **What data are you interested in?** and
**What do you want to learn?** The backend searches Seattle's official Open Data
catalog, inspects candidate datasets, and lets an OpenAI agent choose bounded
queries. It presents explanations, actual result tables, charts, and source links.
No dataset shortlist or SPD-specific query functions are used.

## Run in Windows / VS Code

Use Python 3.12 and Node.js 24 (or a compatible newer LTS). Open this repository
folder in VS Code and install its recommended Python extensions.

```powershell
git pull --ff-only origin review/query-foundation
```

Press **Ctrl+Shift+P > Tasks: Run Task** and run these tasks in order:

1. **Seattle: Set up Python environment**
2. **Seattle: Set up website** (installs Node dependencies and builds the page)
3. **Seattle: Run backend**

Open **http://127.0.0.1:8000/** in your own local browser. `/docs` is still available
for developers, but is not the customer interface. Keep the backend terminal
running; stop it with Ctrl+C. Restart it after building the website for the first
time. F5 is also available through **Seattle: Debug backend** after setup.

If Node is missing, install Node.js LTS, then restart VS Code:

```powershell
winget install --id OpenJS.NodeJS.LTS --exact --source winget
```

For the terminal equivalent, from the repository root:

```powershell
py -3.12 scripts/setup_dev.py
cd frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn seattle_agent.api:app --reload --port 8000
```

## Enable AI analysis

Catalog discovery and the data tools work without an OpenAI key. Automatic
natural-language analysis needs a backend key with model access and API billing.
From the repository root:

```powershell
Copy-Item .env.example .env
code .env
```

Only copy the example if you do not already have a `.env`; preserve existing
settings. Edit `SEATTLE_OPENAI_API_KEY` locally and restart the backend.
**Never send the key in chat, commit it, or put it in frontend settings.** `.env`
is ignored by Git. Without a key, submitting the form still searches the real
catalog and displays dataset matches followed by a clear configuration error.

| Variable | Where | Purpose |
| --- | --- | --- |
| `SEATTLE_OPENAI_API_KEY` | Backend `.env`/environment | OpenAI credential. `OPENAI_API_KEY` is also supported locally as a fallback. |
| `SEATTLE_OPENAI_MODEL` | Backend | Defaults to `gpt-4.1-mini`; choose a tool-calling model your account can access. |
| `SEATTLE_AGENT_MAX_STEPS` | Backend | Defaults to 16 (range 2–32); the final step is reserved for completing the explanation. |
| `SEATTLE_AGENT_TIMEOUT_SECONDS` | Backend | Defaults to 240 (range 1–600); model calls use the remaining time. |
| `SEATTLE_FRONTEND_ORIGINS` | Backend deployment | Comma-separated exact frontend origins for CORS. Local Next dev origins are allowed by default. |
| `NEXT_PUBLIC_API_URL` | Frontend build | HTTPS backend origin for a separate Vercel deployment. No key here. Leave unset when FastAPI serves the website locally. |

## What to try

- Data: **SPD arrest reports**. Question: **How did the monthly count of distinct
  arrest numbers change from January through December 2025? Explain what those
  records represent and any limitations.**
- Data: **building permits**. Question: **Which permit types had the highest row
  counts in 2025? Inspect the definitions and ask if the date field is ambiguous.**

These are requests, not guaranteed answers: the model can ask a clarification if
semantics, dates, or coverage are unclear. You can edit the question and submit
again; each submission is a fresh analysis, not a persistent chat.

## Capabilities and limits

Implemented: dynamic official Seattle catalog search; metadata/schema inspection;
validated projections, counts, distinct-identifier counts, numeric aggregates,
rankings and monthly/yearly trends; one budgeted tool-calling agent loop; streamed
progress; result tables/charts; source/query details, retrieval times and warnings.

**Not supported yet:** cross-dataset joins/correlations, population-adjusted rates,
percentages with independently verified denominators, forecasting, or arbitrary
Python/SQL. Multiple datasets can be inspected/queried independently, but separate
totals do not establish a correlation. Geographic units, dates, identifiers, and
row definitions must be verified before adding that capability.

Counts mean rows unless a distinct identifier is explicitly requested. Rows may
represent reports, offenses, or other records rather than physical incidents.
SPD Arrest Data's description specifically distinguishes arrest reports from
physical in-custody events and flags one-to-many offenses. The tools preserve that
description; they do not declare every row to be a unique arrest.

Trends require an explicit start and exclusive end date. Cached column min/max
values are observations, not proof of continuous coverage. Missing periods are
not zeros; current/boundary periods may be incomplete. Charts are omitted when
results are truncated or grouping would make a single series misleading.

External GIS, files, maps, and other non-native tabular assets are identified as
unsupported. Queries are capped at 100 output rows and 1 MB upstream responses;
aggregate queries can process more input rows. The model sees bounded previews,
not entire datasets. Sources and table values come from actual tool responses;
model prose remains an explanation to assess against those sources.

## How information moves

The form sends two strings to FastAPI. The backend searches the catalog with
Seattle-only domain and official-provenance filters. The model may search again,
inspect discovered IDs, query inspected fields through structured arguments, and
finish with an explanation or clarification. The server rejects invented IDs,
unknown fields, arbitrary SQL, unsupported types, and uninspected queries.

Socrata performs aggregates; no Pandas/DuckDB dependency is needed yet. Tables,
charts, citations, timestamps, and query details come from server-held results,
not invented model output. Data descriptions are treated as untrusted evidence,
never model instructions. The loop has call/iteration/time budgets and explains
failures instead of displaying simulated results.

The agent reuses identical tool results within a request instead of fetching them
again. After repeated failures or redundant calls, it switches to finishing from
existing evidence. Dataset overviews require inspection but no unnecessary count
query. Calculated answers still require a successful query. **Request details**
shows whether a limit came from time, model steps, or completion, plus the last
tool error. If multiple date fields could define "in 2025", the agent should ask
which meaning you intend rather than continuing to search.

The model has separate tools for individual rows (`query`) and summaries
(`aggregate`). The aggregate tool accepts groups and a metric without `columns`;
ranking sort choices such as `value_desc` are translated to the correct aggregate
alias by the server. The shared `/api/query` endpoint and CLI still use the full
validated query contract. A malformed model call is corrected at the tool
boundary; it does not mean the requested ranking is an unsupported operation.

The frontend is Next.js/React, statically built into `frontend/out`. FastAPI serves
it locally, so you only need one server after building. During frontend development
use `npm run dev` in `frontend` and keep FastAPI on port 8000; port 3000 is the
separate development interface.

## Tests and validation

```powershell
.\.venv\Scripts\python.exe -m pytest
cd frontend
npm test
npm run build
npm run typecheck
npx playwright install chromium
npm run test:browser
```

Backend tests cover compiler checks, catalog domain restrictions, schema refresh,
truncation, upstream errors, tool sequencing, missing credentials, and rejection
of unsupported answers. Frontend unit tests cover stream parsing/state; browser
tests exercise the form, errors, tables/charts, and source links with explicitly
synthetic test responses. Those mocks never run in production.

Live Seattle discovery, schema inspection, row counts, and a 12-month 2025 query
were verified during development. A live OpenAI answer was **not** verified because
this workspace has no OpenAI key. Linux/Windows backend CI and frontend CI are
configured; a local pass does not prove hosted CI passed. See
[verification details](docs/INTEGRATION.md).

## Deployment preparation

No website has been published. `render.yaml` prepares the Python backend.
For Vercel, set the project root to `frontend`, use the checked-in `vercel.json`,
and set `NEXT_PUBLIC_API_URL` to the Render backend's HTTPS origin before building.
Set `SEATTLE_FRONTEND_ORIGINS` on Render to the exact Vercel origin. Keep
`SEATTLE_OPENAI_API_KEY` only on Render. Do not deploy the backend's `.env` file.
Complete a live keyed end-to-end test before inviting customers.

Required upstream domains: `api.us.socrata.com`, `data.seattle.gov`, and
`api.openai.com`. Official integration documentation is at `dev.socrata.com`.
The initial documentation access issue has been resolved in this cloud instance.
Current docs describe SODA3 as preferred and requiring authentication/app token;
this version uses Seattle's still-working public SODA 2 resource endpoints, which
are also documented. Migration to SODA3 remains a future integration task.

See [the milestone plan](docs/PLAN.md) and [the VS Code review guide](docs/REVIEW.md).
