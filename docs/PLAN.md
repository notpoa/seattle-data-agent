# Milestones

## 1. Generic, trustworthy data tools

Current partial delivery: query contracts, offline compiler, CLI/API boundaries,
unit and API tests, CI, Windows commands, Render preparation.

Remaining acceptance checks:

1. Read current official Socrata discovery, metadata, datatype, and query docs.
2. Search the Seattle catalog dynamically; do not maintain a dataset shortlist.
3. Normalize metadata: descriptions, column names/types, timestamps, row meaning,
   known coverage, and unsupported asset reasons. Do not infer unknown coverage.
4. Re-inspect dataset schemas before querying; never accept model-invented fields.
5. Execute compiled queries with HTTPS, fixed hosts, timeouts, bounded responses,
   upstream error handling, and redirect restrictions.
6. Return source URL, structured query, request parameters, retrieval time, row
   semantics, and a truncation warning. Detect one-extra-row responses and cap
   response bytes/cells as well as rows. Explain that aggregate input can exceed
   output row limits.
7. Live smoke test: search a topic, choose a returned tabular asset, inspect it,
   query a small projection and an aggregate, and verify source metadata.

Blocked prerequisite: cloud access to official docs and Seattle endpoints.

## 2. One tool-calling agent loop

A backend-only OpenAI client searches first, inspects candidates, and submits
validated queries. Maintain a registry of discovered/inspected dataset IDs.
Reject invented IDs and fields. Budget iterations, calls, duration, and result
size. Supply small results and source records, never entire datasets.

Treat dataset descriptions and rows as untrusted data, not instructions. Use
server-built citations tied to actual tool results. Preserve limitations outside
model-generated prose. Test malformed tool calls, upstream failures, missing
credentials, ambiguous questions, and budget exhaustion.

Require explicit time windows and row definitions; distinguish counts from
rates. Percentages need compatible numerator/denominator evidence; trends need
validated date fields and coverage. Add Pandas or DuckDB only when a bounded
calculation requires them. Do not join unrelated assets without verifying
identifiers, geography, dates, and row meaning.

## 3. Customer website and deployment readiness

Next.js/React: question input, progress, selected datasets, grounded answer,
result table, appropriate charts, and sources. Show errors and clarification
requests visibly. Keep secrets entirely backend-side. Add UI tests, frontend CI,
Vercel configuration, explicit CORS origins, and Render environment setup.

Run the complete browser-to-backend-to-catalog flow locally before deployment.
No Git push or publication without the user's instruction.
