# SearchPaper v0.2–v0.5 实现完整度与外部对标项目核对报告

**核对日期**：2026-07-08
**核对版本**：searchpaper 0.5.0
**测试状态**：`uv run python -m pytest -q` 104 passed；`ruff check/format` clean
**对标项目**：[nature-academic-search](https://github.com/Yuan1z0825/nature-skills/tree/main/skills/nature-academic-search)

---

## 1. 前置 spec 文档实现度核对

spec 来源：

- `dev/01_SearchPaper_Roadmap.md`（roadmap）
- `dev/02_Goal_Mode_Execution_Prompt.md`（/goal 执行 prompt）
- `dev/03_Degradation_and_AntiLoop_Policy.md`（降级策略）
- `dev/04_Agent_Integration_and_Skill_Spec.md`（agent 集成规范）

### 1.1 Priority / 验收项映射表

| # | 要求项 | 状态 | 说明 |
|---|--------|------|------|
| P0 | 保留现有可用行为 | ✅ 已实现 | v0.2–v0.5 核心功能已合并，`searchpaper` CLI 可用 |
| P1 | Core Schema / Adapter Contract | ✅ 已实现 | `WorkRecord`、`SourceRecord`、`WorkIdentifier`、`SearchResult`、`SearchTrace`、`SourceStatus`、`LiteratureSignal`、`SourceError`、`MergeDecision` 均已定义（`src/searchpaper/schemas.py`） |
| P1 | 通用输出 envelope | ✅ 已实现 | 包含 `schema_version`、`object_type`、`data`、`warnings`、`trace` |
| P1 | Adapter Contract（search/get/resolve/status） | ✅ 已实现 | `SourceAdapter` 抽象类已定义（`src/searchpaper/sources/base.py`） |
| P2 | PubMed adapter | ✅ 已实现 | `src/searchpaper/sources/pubmed.py` + fixture tests |
| P2 | Crossref adapter | ✅ 已实现 | `src/searchpaper/sources/crossref.py` + fixture tests |
| P2 | OpenAlex adapter | ✅ 已实现 | `src/searchpaper/sources/openalex.py` + fixture tests |
| P2 | Europe PMC adapter | ✅ 已实现 | 已实现，并扩展了 full-text anchors（v0.5） |
| P2 | Semantic Scholar adapter | ✅ 已实现 | `src/searchpaper/sources/semantic_scholar.py`，支持 citations/references/similar |
| P2 | PubTator3 adapter | ✅ 已实现 | `src/searchpaper/sources/pubtator3.py`，作为 signal 源 |
| P2 | no-key usable 默认 | ✅ 已实现 | 所有核心源无需 API key |
| P3 | Identifier resolution & merge | ✅ 已实现 | `src/searchpaper/merge.py`；合并优先级为 DOI → PMID/PMCID → arXiv → cross-linked IDs → title+year+first author |
| P3 | 保留 provenance/conflicts/merge reasons | ✅ 已实现 | `WorkRecord` 包含 `provenance`、`conflicts`、`merge_reasons` |
| P4 | Literature Signal Model | ✅ 已实现 | `SignalLevel`/`SignalType` 已定义，`interpretation_warning` 默认存在 |
| P5 | Cache / Trace / Storage | ✅ 已实现 | SQLite cache（`src/searchpaper/cache.py`）、`TraceBuilder`（`src/searchpaper/trace.py`） |
| P5 | `cache stats` / `cache clear` / `--no-cache` | ✅ 已实现 | CLI 与 MCP 均支持 |
| P6 | CLI 命令 | ✅/⚠️ | search/get/resolve/expand/context/sources/cache/doctor/capabilities/serve/export/signals/init/install/integrate 均已实现；**`batch` 命令未实现** |
| P7 | MCP 工具 | ✅ 已实现 | search_literature、get_work、resolve_identifiers、get_source_status、search_literature_signals、expand_from_work、export_records、plan_literature_search、lookup_mesh、find_related_articles、convert_identifiers |
| P8 | Agent 集成 install/status/doctor/dry-run/uninstall | ✅ 已实现 | OpenCode/Codex/Claude 均实现，`install --target all` 支持 |
| P8 | managed state 文件 | ⚠️ 部分 | `~/.config/searchpaper/integrations.json` 存在并记录 `managed_files`，**但缺少 spec 示例中的 `config_path` 字段** |
| P9 | Cross-agent skill | ✅ 已实现 | `.agents/skills/literature-search/SKILL.md` 存在 |
| P10 | 文档 | ✅ 已实现 | README、docs/workflows.md、docs/source-catalog.md 覆盖 scope、no-key、degradation、signal limits、non-goals |
| 测试 | schema validation | ✅ 已实现 | `tests/test_schema.py` |
| 测试 | schema snapshot tests | ⚠️ 部分 | 仅有 schema 序列化/roundtrip 测试，**未使用外部快照文件** |
| 测试 | source adapter fixture tests | ✅ 已实现 | `tests/sources/test_*.py` |
| 测试 | merge regression tests | ✅ 已实现 | `tests/test_merge.py` |
| 测试 | cache tests | ✅ 已实现 | `tests/test_cache.py` |
| 测试 | CLI smoke tests | ✅ 已实现 | `tests/test_cli.py` |
| 测试 | MCP mocked tool tests | ✅ 已实现 | `tests/test_mcp.py` |
| 测试 | degraded-source partial success tests | ✅ 已实现 | `tests/test_diagnostics.py`、各 source fixture tests |
| 测试 | installer dry-run tests | ✅ 已实现 | `tests/test_integration.py` |
| 测试 | signal-level serialization tests | ✅ 已实现 | `tests/test_schema.py::test_signal_levels_serialization` |
| 测试 | capabilities output tests | ✅ 已实现 | `tests/test_capabilities.py` |

### 1.2 03 降级策略实现度

| 要求项 | 状态 | 说明 |
|--------|------|------|
| Failure classification | ✅ | `FailureClass` 枚举覆盖 network/timeout/rate_limit/auth/endpoint/schema/parse 等 |
| Source health states | ✅ | `SourceState` 枚举覆盖 available/degraded/offline/rate_limited/not_configured 等 |
| Retry budget | ⚠️ | 策略文档化，但代码层未显式限制“最多 2 次 live debug” |
| Partial success contract | ✅ | `search`/`get`/`resolve` 失败单个源不会导致整体失败 |
| Source requirement modes（optional/preferred/required） | ❌ 未实现 | engine 目前对所有请求源统一视为 optional；CLI/MCP 未暴露 `--require` / `--source-mode` 语义 |
| API key policy | ✅ | no-key usable；key 仅作为加速器；`sources status` 报告 key 配置状态 |
| CI 不依赖 live API | ✅ | 所有 CI 测试使用 fixture/respx |

### 1.3 04 Agent 集成规范实现度

| 要求项 | 状态 | 说明 |
|--------|------|------|
| CLI-first + MCP + thin agent wrappers | ✅ | 架构符合 |
| OpenCode 优先 | ✅ | `searchpaper install --target opencode` 完整 |
| Codex / Claude 同层支持 | ⚠️ | scaffold 实现：生成 instructions/MCP snippet；OpenCode 是唯一写入用户 config 的目标 |
| Installer 安全规则 | ✅ | dry-run、backup、marker-delimited block、uninstall 仅删除 managed 内容 |
| Managed state | ⚠️ | 见 1.1；缺少 `config_path` 字段 |
| Skill location & content | ✅ | `.agents/skills/literature-search/SKILL.md` 内容覆盖使用时机、证据边界、降级源、导出 |
| OpenCode custom tool wrapper | ❌ 未实现 | 仅有 MCP 配置与 skill，无 thin custom tool wrapper |
| Capabilities command | ✅ | `searchpaper capabilities --json` 输出 commands/tools/sources/formats/integrations |

### 1.4 未实现 / 部分实现清单（spec 角度）

1. **`searchpaper batch ... --jsonl`**（02 Stretch / 推荐）未实现。
2. **Source requirement modes**（03 §7）未在 engine 中实现，CLI 未暴露。
3. **OpenCode custom tool wrapper**（04 §13）未实现。
4. **Schema snapshot tests** 仅为内存序列化测试，未生成/比对磁盘快照文件。
5. **Managed state 字段完整性**：`integrations.json` 缺少 `config_path` 字段（04 §8 示例）。
6. **Retry budget  enforcement**：策略有文档，代码无显式计数/熔断。

---

## 2. nature-academic-search 功能覆盖核对

### 2.1 MCP 工具面覆盖

nature-academic-search 暴露大量 source-specific MCP 工具；SearchPaper 采用“小稳定 MCP 面 + source 参数”的架构。功能等价性如下：

| nature 工具 | SearchPaper 对应 | 覆盖状态 |
|-------------|------------------|----------|
| `pubmed_search_articles` | `search_literature` + `--sources pubmed` | ✅ 功能覆盖 |
| `search_crossref` | `search_literature` + `--sources crossref` | ✅ 功能覆盖 |
| `search_arxiv` | `search_literature` + `--sources arxiv` | ✅ 功能覆盖 |
| `search_semantic_scholar` | `search_literature` + `--sources semantic_scholar` | ✅ 功能覆盖 |
| `search_biorxiv` / `search_medrxiv` | `search_literature` + `--sources biorxiv/medrxiv` | ✅ 功能覆盖 |
| `search_google_scholar` | 未实现（T3 scraped，按设计 catalog 但不查询） | ❌ 不覆盖 |
| `search_webofscience` | 未实现（T3 institutional） | ❌ 不覆盖 |
| `search_scopus` | 未实现（T3 institutional） | ❌ 不覆盖 |
| `pubmed_fetch_articles` | `get_work --pmid ...` / `resolve --pmid ...` | ✅ 功能覆盖 |
| `pubmed_find_related` | `pubmed related` / MCP `find_related_articles` | ✅ 功能覆盖 |
| `pubmed_format_citations` | `export --format bibtex/ris/...` | ⚠️ 部分覆盖（缺少 APA/MLA） |
| `pubmed_convert_ids` | `pubmed convert-ids` / MCP `convert_identifiers` | ✅ 功能覆盖 |
| `pubmed_lookup_mesh` | `pubmed mesh` / MCP `lookup_mesh` | ✅ 功能覆盖 |
| `pubmed_lookup_citation` | 无直接对应；可用 `search_literature` 近似 | ⚠️ 部分覆盖 |

### 2.2 工作流覆盖

| WF | 名称 | 状态 | 说明 |
|----|------|------|------|
| WF1 | Multi-source search | ✅ | `searchpaper search` / `plan` / `sources tiers` 完整覆盖 |
| WF2 | Citation verification | ❌ | 无 citation parser、无 .docx/.tex/.txt 文档导入、无 verified/mismatch/suspicious 分类 |
| WF3 | MeSH search strategy | ✅ | `pubmed mesh` 支持；spell-check 未实现 |
| WF4 | Citation file management | ⚠️ | `references convert` 支持 refs.txt（DOI/PMID/arXiv）并输出 .nbib/.ris/.bib；**不支持 refs.txt 中的 `QUERY:`、`AUTHOR:... TITLE:...` 行**；无独立 `format-converter.py` 多源下载器 |
| WF5a | Find related papers | ✅ | `pubmed related` + `expand` 覆盖 |
| WF5b | BibTeX generation | ✅ | `export --format bibtex` 覆盖 |
| WF5c | ID conversion | ✅ | `pubmed convert-ids` 覆盖 |
| WF5d | Citation formatting | ⚠️ | 支持 BibTeX/RIS/Markdown/NBIB/ENW；**不支持 APA/MLA** |
| WF5e | Full-text access | ⚠️ | v0.5 可报告 full-text availability、OA PDF URL、Europe PMC anchors；**不下载/解析全文**（符合 non-goal） |

### 2.3 共享模块覆盖

| 模块 | nature 文件 | SearchPaper 对应 | 状态 |
|------|-------------|------------------|------|
| Dedup Engine | `references/dedup-engine.md` | `src/searchpaper/merge.py` | ✅ DOI 主键 + title+first author Jaccard fallback 已实现 |
| Citation Parser | `references/citation-parser.md` | 无 | ❌ 未实现 |
| Search Strategy | `references/search-strategy.md` | `src/searchpaper/planner.py` + `src/searchpaper/source_catalog.py` | ⚠️ 有 profile/source tiers，缺少完整 query templates 和 combined scoring |
| RIS/BibTeX Format | `references/ris-bibtex-format.md` | `src/searchpaper/export.py` | ⚠️ 字段映射基本覆盖，但未完全对齐 MEDLINE→RIS/BibTeX 的所有细节（如 `AN  - PMID:` 前缀、页码 split） |
| Format Converter | `scripts/format-converter.py` | `src/searchpaper/reference_convert.py` | ⚠️ 仅支持 refs.txt 中的 DOI/PMID/arXiv；不支持按 query/author+title 搜索后下载 |

### 2.4 Source Tiers 覆盖

| Tier | nature 源 | SearchPaper 状态 |
|------|-----------|------------------|
| T1 | PubMed, CrossRef, arXiv | ✅ 全部实现 |
| T2 | Semantic Scholar, bioRxiv, medRxiv | ✅ 全部实现 |
| T3 | Google Scholar, Web of Science, Scopus | ❌ 按设计 catalog 但不自动查询（因 scraped/institutional） |
| 中文 | CNKI / 万方 | ❌ 按设计 catalog 为 manual gap |

---

## 3. 量化总结

### 3.1 spec 实现度

- **已实现/符合**：约 85–90%（核心 schema、adapter contract、CLI/MCP、source adapters、cache/trace、merge、export、integrations、skill 均到位）
- **部分实现**：约 8%（schema snapshot tests、managed state 字段、Codex/Claude scaffold 深度）
- **未实现**：约 5%（batch 命令、source requirement modes、OpenCode custom tool wrapper）

### 3.2 nature-academic-search 功能覆盖度

- **完全覆盖**：WF1 多源搜索、WF3 MeSH、WF5a 相关文献、WF5b BibTeX、WF5c ID 转换、T1/T2 源
- **部分覆盖**：WF4 引用文件管理（refs.txt 不完整）、WF5d 引用格式化（缺 APA/MLA）、WF5e 全文访问（仅元数据层）、Search Strategy/RIS/BibTeX 细节
- **未覆盖**：WF2 引用验证（ citation parser + 文档导入 + 验证分类）、T3 源（Google Scholar/WoS/Scopus）、中文库 CNKI/万方

**整体功能覆盖度**：约 75–80%（按功能点计），核心搜索/解析/导出已对齐，citation verification 是最显著缺口。

---

## 4. 建议补齐项

按优先级排序：

1. **Source requirement modes**（高）：在 `SearchEngine.search/get/resolve` 中支持 optional/preferred/required，CLI 增加 `--source-mode` / `--require` 语义。这直接关系到 03 降级策略的完整实现。
2. **`searchpaper batch` 命令**（中）：支持 JSONL/文本输入批量解析/搜索/导出，与 02 Stretch 对齐。
3. **OpenCode custom tool wrapper**（中）：按 04 §13 实现 thin wrapper，调用 `searchpaper search ... --json` 并返回解析后的 JSON，不重复核心逻辑。
4. **补充 managed state 字段**（低）：在 `integrations.json` 中记录 `config_path` 等字段，与 04 §8 示例一致。
5. **Schema snapshot tests**（低）：使用 `pytest-snapshot` 或 syrupy 生成真实快照文件。
6. **WF2 Citation verification**（视 v0.6 规划而定）：这是 nature 项目的重要差异化功能，若 SearchPaper 希望覆盖，需要新增 citation parser（.docx/.tex/.txt）和 verified/mismatch/suspicious 分类输出。
7. **WF4 refs.txt 增强**（低）：支持 `QUERY:`、`AUTHOR:... TITLE:...` 行，或至少明确文档说明当前仅支持 identifier 行。
8. **APA/MLA 输出**（低）：扩展 `export.py` 支持两种常用引用格式。

---

## 5. 结论

SearchPaper v0.5.0 已实现其自身 roadmap/spec 中 v0.2–v0.5 的绝大部分目标，架构稳定、测试通过、lint clean，且严格遵循了“不做 PDF 解析、不做研究 agent、不做结论生成”的 non-goals。与 nature-academic-search 相比，**核心多源搜索、标识符解析、MeSH、ID 转换、BibTeX 导出已完全对齐**；主要差距集中在 **citation verification（WF2）**、**T3/institutional 源**、以及 **refs.txt/AUTHOR+TITLE/APA/MLA 等引用工作流细节**。这些差距多数符合 SearchPaper 自身的 scope 边界，若需进一步覆盖，可作为 v0.6+ 的明确交付项。
