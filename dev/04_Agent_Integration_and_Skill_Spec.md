# SearchPaper Agent Integration and Skill Specification

This document defines how SearchPaper should adapt smoothly to OpenCode, Codex, and Claude without becoming a wrapper tied to one agent.

## 1. Integration Principle

SearchPaper should be CLI-first, MCP-compatible, and skill-guided.

The project should not be built around a single agent. The stable core should be usable through:

1. Python library calls;
2. CLI commands;
3. MCP tools;
4. thin OpenCode custom tools or plugin wrappers;
5. cross-agent skills/instructions.

OpenCode should be implemented first because it is important for cost-sensitive research workflows, but Codex and Claude should not be second-class in architecture.

## 2. Layered Integration Model

```text
Python core
  ↓
CLI
  ↓
MCP server
  ↓
Agent integrations
  ├─ OpenCode
  ├─ Codex
  └─ Claude
  ↓
Skills / AGENTS.md behavior rules
```

The CLI and core own the real behavior. MCP and agent wrappers are adapters.

## 3. CLI as Stable Contract

The CLI should remain usable even without MCP.

Minimum commands:

```bash
searchpaper search "query" --json
searchpaper get --pmid ID --json
searchpaper resolve --doi DOI --json
searchpaper sources status
searchpaper capabilities --json
searchpaper doctor
searchpaper serve --mcp
```

Agents should be able to fall back to CLI if MCP configuration fails.

## 4. MCP Tool Surface

Keep MCP tools stable and small.

Recommended tools:

- `search_literature`
- `get_work`
- `resolve_identifiers`
- `expand_from_work`
- `search_literature_signals`
- `export_records`
- `get_source_status`

Avoid source-specific MCP tools by default.

Tool outputs should match core schemas and include schema version, warnings, and trace.

## 5. OpenCode First Implementation

OpenCode support should be implemented first.

Minimum OpenCode integration:

```bash
searchpaper install --target opencode
searchpaper integrate dry-run --target opencode
searchpaper integrate status
searchpaper integrate doctor
searchpaper integrate uninstall --target opencode
```

Recommended modes:

```text
opencode:mcp
opencode:skill
opencode:custom_tool
opencode:both
```

v0.2 should at least support MCP config and skill installation. A thin custom tool wrapper can be added if useful.

## 6. Codex and Claude Support

Codex and Claude should receive equivalent architectural treatment:

- MCP config generation;
- skill installation or compatible instruction file;
- doctor check;
- dry-run;
- uninstall of managed files.

Do not hard-code assumptions that only OpenCode exists.

## 7. Installer / Integration Manager

The installer should be treated as a small integration manager, not a one-shot shell script.

Minimum v0.2 commands:

```bash
searchpaper install --target opencode
searchpaper install --target codex
searchpaper install --target claude
searchpaper install --target all
searchpaper integrate status
searchpaper integrate dry-run --target opencode
searchpaper integrate doctor
searchpaper integrate uninstall --target opencode
```

Minimum behavior:

- detect existing agent config;
- generate config snippets;
- write only managed sections or managed files;
- backup before modifying user config;
- record managed files;
- support dry-run;
- support uninstall.

## 8. Managed State

Maintain a state file such as:

```text
~/.config/searchpaper/integrations.json
```

Example structure:

```json
{
  "schema_version": "0.2",
  "searchpaper_version": "0.2.0",
  "installed_targets": {
    "opencode": {
      "modes": ["mcp", "skill"],
      "scope": "user",
      "config_path": "~/.config/opencode/opencode.jsonc",
      "managed_files": [
        "~/.config/opencode/skills/literature-search/SKILL.md"
      ],
      "installed_at": "..."
    }
  }
}
```

Do not rely on memory or README instructions to know what SearchPaper installed.

## 9. Safe File Modification Rules

The installer must follow these rules:

1. Use dry-run before writing when requested.
2. Create backups before modifying user-owned config.
3. Prefer adding managed files over editing user files.
4. If editing text files, use marker-delimited blocks:

```text
<!-- searchpaper:start -->
...
<!-- searchpaper:end -->
```

5. Do not overwrite unknown user content.
6. Uninstall should remove only managed files and managed blocks.
7. Doctor should detect broken configs and provide repair suggestions.

## 10. Skill Location

Preferred cross-agent location:

```text
.agents/skills/literature-search/SKILL.md
```

Agent-specific copies may be generated only if necessary:

```text
.opencode/skills/literature-search/SKILL.md
.codex/skills/literature-search/SKILL.md
.claude/skills/literature-search/SKILL.md
```

Avoid maintaining divergent skill content unless required.

## 11. Skill Content Requirements

The skill should teach behavior, not repeat the full API docs.

It must tell agents:

- SearchPaper is for literature search, identifier resolution, provenance, and export.
- It is not a research conclusion engine.
- Prefer multi-source search before narrow expansion.
- Preserve DOI/PMID/PMCID/source provenance.
- Treat literature signals as signals, not evaluated scientific conclusions.
- Check `sources status` when results are unexpectedly weak.
- Use JSON/JSONL for downstream workflows.
- Report degraded sources instead of hiding them.
- Do not repeatedly call unreliable endpoints.

## 12. Draft Skill Text

Suggested `SKILL.md` content:

```markdown
# Literature Search with SearchPaper

Use SearchPaper when a task requires scholarly literature search, paper metadata, DOI/PMID/PMCID resolution, citation/context expansion, biomedical literature signals, or exportable literature records.

SearchPaper is not a research agent and does not evaluate scientific truth. It returns literature records, provenance, identifiers, and signals that must be interpreted by the user or a downstream research workflow.

## Preferred Workflow

1. Start with `searchpaper search "<query>" --json` or MCP `search_literature`.
2. Preserve DOI, PMID, PMCID, source, and trace fields.
3. Use `resolve_identifiers` or `searchpaper resolve` when merging or checking a known paper.
4. Use `expand_from_work` only after identifying a reliable seed paper.
5. Use `search_literature_signals` for biomedical entity/relation signals, but do not call those signals proof.
6. If results are sparse or suspicious, call `get_source_status` or `searchpaper sources status`.
7. Export machine-readable results with JSONL when passing results to downstream agents.

## Interpretation Rules

- A literature signal is not an evaluated conclusion.
- A PubTator or abstract co-mention signal does not prove causality.
- A single relevant paper is still a useful literature-backed record, but the agent must report its source and limitations.
- Do not hide degraded or failed sources.
- Do not retry a broken public API repeatedly.

## Output Rules

When summarizing SearchPaper results, include:

- title;
- year;
- DOI/PMID/PMCID when available;
- source provenance;
- signal level if using signals;
- warnings or degraded-source notes.
```

## 13. OpenCode Custom Tool Wrapper

If implemented, the OpenCode custom tool should be thin.

It may:

- accept a query;
- call `searchpaper search ... --json`;
- return parsed JSON;
- expose a limited set of high-value commands.

It must not:

- duplicate source adapter logic;
- implement independent ranking;
- maintain separate cache;
- diverge from CLI schemas.

## 14. Capabilities Command

SearchPaper should expose capabilities:

```bash
searchpaper capabilities --json
```

Example:

```json
{
  "schema_version": "0.2",
  "cli_commands": ["search", "get", "resolve", "sources status", "doctor"],
  "mcp_tools": ["search_literature", "get_work", "resolve_identifiers"],
  "sources": ["pubmed", "crossref", "openalex", "europepmc"],
  "export_formats": ["json", "jsonl", "bibtex", "ris", "markdown"],
  "agent_integrations": ["opencode", "codex", "claude"]
}
```

Agents should prefer capabilities over assuming tool availability.

## 15. Future Extension

v0.3+ may add:

- integration update/migration;
- OpenCode plugin wrapper;
- additional agent adapters;
- remote MCP mode;
- richer project mode;
- Zotero/Obsidian hooks.

These should extend the integration manager rather than rewrite the architecture.

## 16. Final Rule

Agent integration should make SearchPaper easy to use, not define what SearchPaper is.

The stable product is the core + CLI + schema. MCP and skills make it agent-native. Plugins and wrappers are convenience layers.
