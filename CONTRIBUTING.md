# Contributing to paperSearch

Thanks for your interest in improving paperSearch. This is a small, focused MCP
server, so contributions of any size are welcome.

## Development setup

```bash
git clone https://github.com/freddiewho/paperSearch
cd paperSearch
uv sync --extra dev
```

## Running checks

Before opening a pull request, make sure the full check suite passes:

```bash
uv run ruff check .      # lint
uv run pytest -q         # tests
```

Optionally, run the live smoke test (hits Semantic Scholar and PubTator3):

```bash
uv run python scripts/smoke_test.py
```

## Guidelines

- Keep tools returning the normalized envelope (`source`, `query`,
  `retrieved_at`, `cache_key`, `from_cache`, `raw_ids`, `items`, `warnings`).
- Prefer returning structured error envelopes over raising exceptions from tools.
- Add or update mocked tests (`respx`) for any new network behavior.
- Do not commit `.env`, `config.json`, or any API keys.

## Reporting issues

Open an issue with the tool name, the arguments you called it with, and the
returned `warnings` (redact any keys). Reproduction steps help a lot.
