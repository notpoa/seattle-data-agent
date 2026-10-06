# Official integration documentation and evidence

Documentation access attempted during this task:

- https://dev.socrata.com/docs/other/discovery
- https://dev.socrata.com/docs/queries/
- https://dev.socrata.com/docs/datatypes/

All returned `Tunnel connection failed: 403 Forbidden`. Therefore their current
contents have **not** been reviewed, and no production Socrata transport is
implemented. These links are references to verify, not a claim of API validation.

Requests to the candidate catalog host and Seattle metadata host were blocked by
the same proxy. No dataset IDs, schema fields, row results, or live citations
were obtained. Test fixtures are explicitly synthetic and confined to tests.

Before enabling real transport, verify against current official documentation:

- Catalog endpoint/version, domain restriction, pagination, query fields, and
  asset types; defensively enforce Seattle domain on every returned candidate.
- Metadata endpoint, resource identity, asset/view semantics, columns, datatypes,
  timestamps, and available coverage information. Do not assume every catalog
  result is a queryable table.
- Supported dataset query API and version, parameter syntax, identifier rules,
  string literal escaping, aggregates, nulls, timestamps/timezones, limits,
  authentication/app-token recommendations, rate limits, and errors.
- When redirects or external service assets are present, explain unsupported
  assets instead of following arbitrary URLs.
- Test actual upstream behavior separately from mocked transport tests.

Capture documentation reviewed and live-check evidence here when access works.
