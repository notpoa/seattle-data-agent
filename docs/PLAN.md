# Milestones and remaining work

## Delivered: simple website and generic analysis loop

Two-question Next.js/React interface; automatic official Seattle catalog discovery;
metadata inspection; generic bounded queries; row/distinct counts, numeric
aggregates, rankings, and monthly/yearly trends; a single OpenAI tool-calling loop;
progress, errors/clarifications, tables, suitable charts, and actual source/query
records. Backend and frontend tests and CI are maintained. Windows VS Code setup
and startup tasks are included. Render/Vercel configuration is prepared.

Live catalog and query checks pass. No keyed OpenAI analysis has been run because
this environment has no model credential. Complete that check before describing
the complete agent as live-validated.

## Next: deeper validation and calculations

Add independently verifiable row-grain decisions and continuous coverage checks,
formal numerator/denominator validation for percentages and rates, more complete
clarification follow-ups, and stronger claim-to-result validation for model prose.
Add Pandas/DuckDB only for bounded calculations that need them. Migrate to SODA3
when authentication/app-token setup is available and the supported response format
has been checked. Keep unsupported assets explicit.

## Later: multiple-dataset relationships

Verify shared identifiers, geographic units, temporal alignment, and record grain
before joins or correlations. Account for duplicate identifiers and missing data.
Never infer relationships from unrelated totals. Cross-dataset correlations and
joins remain unsupported in this release.

## Deployment acceptance

Run the browser-to-backend-to-catalog-to-model flow with a real backend credential.
Verify model access/billing, source fidelity, ambiguity handling, and failures.
Review exact CORS origins and frontend/backend configuration before deployment.
Do not publish the website without the user's instruction. Review-branch pushes
were authorized in this session; deployment was not.
