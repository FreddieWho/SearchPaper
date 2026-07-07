# SearchPaper Degradation and Anti-Loop Policy

This document exists because SearchPaper depends on multiple public/open APIs, and public APIs are not guaranteed to be reliable, stable, fast, or uniformly documented.

The goal is not to skip difficult implementation. The goal is to prevent `/goal` mode from wasting time on meaningless loops when an external source is temporarily broken, rate-limited, schema-shifted, or poorly documented.

## 1. Core Principle

A source adapter may be degraded. The whole system must not be degraded because one source fails.

The correct fallback is:

```text
stable contract + fixture-backed tests + clear source status + partial results
```

The wrong fallback is:

```text
retry forever + block all progress + no trace + no usable output
```

## 2. Failure Classification

Every source failure should be classified. Do not collapse all failures into `Exception`.

Recommended classes:

- `network_error`
- `timeout`
- `rate_limited`
- `auth_required`
- `invalid_api_key`
- `endpoint_unavailable`
- `schema_changed`
- `empty_result`
- `unsupported_query`
- `parse_error`
- `validation_error`
- `unknown_error`

Each failure should include:

- source name;
- endpoint or operation;
- query or identifier type, not sensitive raw payload if avoidable;
- timestamp;
- retry count;
- whether fallback was used;
- user-visible warning.

## 3. Source Health States

Each adapter should report a health state through `sources status` and MCP `get_source_status`.

Recommended states:

```text
available
available_with_key_optional
available_with_key_required
degraded
rate_limited
offline
not_configured
not_implemented
```

A degraded source is still a valid implementation state if:

- the adapter contract exists;
- fixture-backed tests pass;
- the source returns clear warnings;
- other sources continue working.

## 4. Retry Budget

In `/goal` mode, do not spend unlimited effort on a single live API.

Recommended retry budget:

- per request: 1 retry after transient failure;
- per source endpoint during implementation: at most 2 focused live-debug attempts;
- per source endpoint time budget: roughly 15 minutes of focused debugging;
- after budget exhaustion: mark source degraded, add fixture-backed behavior, continue.

Do not interpret this as permission to skip implementation. The adapter must still be modeled and tested using fixtures or documented sample payloads.

## 5. Degraded Adapter Requirements

A degraded adapter must not be an empty stub unless the source is explicitly deferred.

A valid degraded adapter should include:

1. source adapter class;
2. schema mapping from sample or fixture response;
3. mocked tests;
4. `status()` implementation;
5. clear warning message;
6. documentation note;
7. TODO with exact reason for degradation.

Example warning style:

```json
{
  "source": "europepmc",
  "status": "degraded",
  "warning": "Europe PMC live request failed during this run. Fixture-backed adapter contract is implemented; live API should be rechecked later.",
  "failure_class": "timeout"
}
```

## 6. Partial Success Contract

A multi-source search must return partial results if at least one source succeeds.

The response should include:

- succeeded sources;
- degraded sources;
- failed sources;
- source errors;
- result count by source;
- merged result count;
- warnings.

A single source failure should not cause process exit code failure unless the user requested only that source and marked it required.

Recommended behavior:

```bash
searchpaper search "query" --sources pubmed,crossref,openalex --json
```

If Crossref fails but PubMed and OpenAlex succeed, return results with warnings.

If all sources fail, return a structured error with diagnostics and nonzero exit code.

## 7. Source Requirement Modes

Support source requirement modes internally, even if the CLI only exposes a simple interface early.

Recommended modes:

```text
optional: use if available, warn if failed
preferred: use if available, warn more loudly if failed
required: fail the command if unavailable
```

Default source mode should be `optional` or `preferred`, not `required`.

## 8. API Key Policy

SearchPaper should be no-key usable by default.

If a source works better with an API key:

- document the key;
- detect whether configured;
- report in `sources status`;
- do not fail core search if absent unless user requested key-only behavior.

Do not hide key-related degradation.

## 9. Live API and CI Policy

CI must not require live public APIs.

Use:

- mocked HTTP responses;
- sample payload fixtures;
- schema snapshots;
- adapter contract tests.

Live API tests may exist but should be:

- optional;
- manually triggered;
- skipped unless environment variable is set;
- not required for merge/CI success.

## 10. Areas Where Agents May Loop

### 10.1 Multi-source fetch perfection

Risk: agent keeps trying to make every source live-perfect.

Policy: once adapter contract and mocked tests pass, live instability becomes degraded status, not a blocker.

### 10.2 Naming bikeshed

Canonical names:

- Display: SearchPaper
- Package: searchpaper
- CLI: searchpaper
- MCP: searchpaper

Do not rename during `/goal`.

### 10.3 Evidence vs signal wording

Internal schema should use `LiteratureSignal` / `RelationSignal` and signal levels.

User-facing docs may mention evidence-linked literature records, but the tool must not claim evaluated evidence.

Do not loop on wording.

### 10.4 PDF and full text

v0.2 does not implement PDF parsing or full-text indexing.

It may return OA links, PMCID, Europe PMC/PMC links, and future anchor fields.

Do not start PDF parsing.

### 10.5 Tool surface expansion

MCP should expose a small stable tool surface.

Do not add source-specific MCP tools by default.

Source-specific debug commands may exist in CLI only.

### 10.6 Ranking perfection

v0.2 uses transparent rule-based ranking.

Do not implement LLM reranking by default.

Do not spend large effort tuning weights.

### 10.7 Installer perfection

v0.2 installer must support detect/install/status/doctor/dry-run/uninstall.

Do not implement a full external adapter ecosystem in v0.2.

Do not block v0.2 on complex migration support.

### 10.8 UI

No UI in v0.2.

### 10.9 Graph database

No Neo4j or heavy graph DB in v0.2.

Use SQLite and logical graph structures.

### 10.10 Zotero/Obsidian

Export BibTeX/RIS/JSONL/Markdown first.

Do not implement direct Zotero/Obsidian integration in v0.2.

## 11. Escalation Decision Tree

When a source API fails:

```text
1. Is the source required for the current command?
   - yes: return structured error if no fallback is available.
   - no: continue.

2. Did another source produce usable results?
   - yes: return partial success with warning.
   - no: try minimal fallback or return structured all-source failure.

3. Is the adapter contract implemented and tested with fixtures?
   - yes: mark degraded and continue roadmap.
   - no: implement fixture-backed adapter contract before moving on.

4. Is the failure due to ambiguous schema or endpoint docs?
   - yes: preserve raw payload, map minimal fields, add warning.

5. Has retry budget been exhausted?
   - yes: stop live debugging and continue.
```

## 12. Minimum Acceptable Degradation Output

A degraded source should still provide status like:

```json
{
  "source": "semantic_scholar",
  "state": "rate_limited",
  "key_configured": false,
  "last_checked_at": "...",
  "last_error_class": "rate_limited",
  "live_search_available": false,
  "fixture_tests_available": true,
  "message": "Source is not blocking multi-source search; use API key or retry later for enrichment."
}
```

## 13. Agent Behavior Rule

When blocked by unreliable external behavior, the agent should produce a useful degraded implementation and move forward.

When blocked by internal design ambiguity, the agent should choose the simpler option that preserves:

1. schema stability;
2. provenance;
3. partial success;
4. future extensibility;
5. CLI usability.

## 14. Final Rule

SearchPaper should fail visibly, partially, and recoverably.

It should not fail silently, globally, or endlessly.
