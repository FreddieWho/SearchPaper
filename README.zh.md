<p align="center">
  <img src="docs/assets/searchpaper-banner.png" alt="SearchPaper banner" width="100%">
</p>

# SearchPaper 中文文档

[English README](README.md)

**SearchPaper** 是一个面向 agent 辅助研究的文献检索基础设施层。它跨开放学术源检索文献、规范化标识符、保守合并重复记录、保留来源出处，并导出可追踪结果，供后续 agent 或人工审阅使用。

SearchPaper **不是**完整研究 agent、系统综述引擎、证据评估器、PDF 解析器或 Zotero 替代品。它提供结构化文献记录和 provenance；解释与判断仍由用户或下游研究流程完成。

## 🔎 一眼看懂

| 范围 | SearchPaper 提供什么 |
|---|---|
| 📚 数据源 | PubMed、Crossref、OpenAlex、Europe PMC、arXiv、bioRxiv、medRxiv、Semantic Scholar、Unpaywall、OpenCitations、PubTator3 |
| 🧬 生物医学流程 | MeSH 查询、PubMed 相关文章、DOI/PMID/PMCID 转换、PubTator3 文献信号 |
| 🔗 标识符 | DOI、PMID、PMCID、arXiv、OpenAlex、Semantic Scholar ID |
| 🧾 可追踪性 | 来源记录、合并原因、冲突、warning、trace 字段 |
| 🧠 Agent 访问 | CLI + MCP tools，支持 OpenCode、Codex、Claude 和其他 MCP client |
| 📦 导出 | JSON、JSONL、BibTeX、RIS、NBIB、ENW、Markdown、Zotero CSV、Obsidian notes、APA、MLA |
| 🔓 API key | 核心流程默认无需 key；可选 key 可提升速率和覆盖 |

## ✨ 核心能力

- **多源文献检索**：跨开放学术 API 查询。
- **标识符解析**：支持常见学术 ID。
- **保守去重合并**：保留 provenance、冲突和合并原因。
- **本地 SQLite 缓存**：提升速度并便于复现。
- **全文就绪信息**：OA 链接、Europe PMC XML anchors、全文可用性字段。
- **结构化文献信号**：来自 PubTator3，并带解释边界。
- **CLI-first 工作流**：同时提供小而稳定的 MCP tool surface。
- **Agent 集成**：支持 OpenCode、Codex、Claude。

## ⚡ 快速开始

```bash
git clone <repo-url> ~/Publish/PaperSearch
cd ~/Publish/PaperSearch
uv sync --extra dev
uv run pytest -q
```

| 任务 | 命令 |
|---|---|
| 搜索文献 | `uv run searchpaper search "HCC TACE PD-1" --json` |
| 解析 DOI | `uv run searchpaper resolve --doi 10.1038/s41586-021-03819-2 --json` |
| 查看源健康状态 | `uv run searchpaper sources status --json` |
| 运行诊断 | `uv run searchpaper doctor` |
| 启动 MCP server | `uv run searchpaper serve --mcp` |

本地可编辑安装：

```bash
uv pip install -e .
```

安装后会提供 `searchpaper` CLI。

## ⚙️ 配置

SearchPaper 读取 `~/.config/searchpaper/config.json`，环境变量优先覆盖文件值。

```json
{
  "semantic_scholar_api_key": "YOUR_KEY",
  "crossref_email": "you@example.com",
  "openalex_email": "you@example.com",
  "ncbi_api_key": "YOUR_NCBI_KEY",
  "cache_path": "~/.cache/searchpaper/cache.db"
}
```

| 环境变量 | 对应配置 | 说明 |
|---|---|---|
| `SEARCHPAPER_CACHE` | `cache_path` | SQLite 缓存文件 |
| `SEARCHPAPER_CONFIG` | `config_path` | 配置文件路径 |
| `SEMANTIC_SCHOLAR_API_KEY` | `semantic_scholar_api_key` | 可选 Semantic Scholar key |
| `CROSSREF_EMAIL` | `crossref_email` | Crossref 礼貌池邮箱 |
| `OPENALEX_EMAIL` | `openalex_email` | OpenAlex 礼貌池邮箱 |
| `NCBI_API_KEY` | `ncbi_api_key` | 可选 NCBI key |

## 🧭 常用 CLI 工作流

| 工作流 | 命令 |
|---|---|
| 规划源路由 | `searchpaper plan "query" --profile auto --json` |
| 搜索文献 | `searchpaper search "query" --json` |
| 按 PMID 获取作品 | `searchpaper get --pmid 12345 --json` |
| 解析标识符 | `searchpaper resolve --doi 10.xxx --json` |
| 从种子论文扩展 | `searchpaper expand --doi 10.xxx --by citations,references --json` |
| 构建上下文包 | `searchpaper context --doi 10.xxx --json` |
| 获取全文 anchors | `searchpaper get --pmcid PMC8371605 --sources europepmc --anchors --json` |
| 探测源 | `searchpaper sources preflight --sources pubmed,arxiv --json` |
| 解释源行为 | `searchpaper sources explain pubmed` |
| 诊断源健康 | `searchpaper sources diagnose --json` |
| 保存项目 trace | `searchpaper search "query" --json --save` |
| 导出已保存 trace | `searchpaper project export <trace_id> --format bibtex` |
| 查询 MeSH | `searchpaper pubmed mesh "term" --json` |
| 查 PubMed 相关文章 | `searchpaper pubmed related 12345 --json` |
| 转换 PubMed ID | `searchpaper pubmed convert-ids 10.xxx --json` |
| 批处理输入 | `searchpaper batch queries.jsonl --format jsonl --output results.jsonl` |
| 验证参考文献 | `searchpaper references verify refs.txt --output-format markdown` |
| 导出结果 | `searchpaper export results.json --format bibtex` |
| 查看能力 | `searchpaper capabilities --json` |

## 🧩 MCP 与 Agent 集成

启动默认 stdio MCP server：

```bash
searchpaper serve --mcp
```

安装 `searchpaper[remote]` 后可启动 HTTP/SSE MCP server：

```bash
searchpaper serve --mcp --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

| Tool | 用途 |
|---|---|
| `search_literature` | 多源文献检索 |
| `plan_literature_search` | 不发起 live search 的源路由规划 |
| `get_work` | 按标识符获取单篇作品 |
| `resolve_identifiers` | 批量解析并合并标识符 |
| `get_source_status` | 源健康状态和可选 catalog |
| `lookup_mesh` | PubMed MeSH descriptor 查询 |
| `find_related_articles` | PubMed 相关文章 ID |
| `convert_identifiers` | DOI/PMID/PMCID 转换 |
| `search_literature_signals` | 生物医学实体/关系信号 |
| `expand_from_work` | 引用、参考文献、相关论文扩展 |
| `export_records` | 导出结构化记录 |

| Agent | 安装命令 | 产物 |
|---|---|---|
| OpenCode | `searchpaper install --target opencode` | MCP 配置 + `literature-search` skill |
| Codex | `searchpaper install --target codex` | MCP snippet + SearchPaper instructions |
| Claude | `searchpaper install --target claude` | MCP snippet + SearchPaper instructions |
| 全部 | `searchpaper install --target all` | 生成全部支持的集成脚手架 |

生成文件后，请检查并在 agent 设置中启用 `searchpaper` MCP server。

## 📖 全文就绪能力

SearchPaper 可以报告全文可用性，但不要求 PDF 解析。记录中可能包含 `full_text_availability`、`open_access_pdf`，以及 `doi`、`pubmed`、`pmc`、`oa_url`、`oa_pdf_url` 等 canonical URL。

```bash
searchpaper resolve --doi 10.1038/s41586-021-03819-2 --json
searchpaper get --pmcid PMC8371605 --sources europepmc --anchors --json
searchpaper context --doi 10.1038/s41586-021-03819-2 --json
searchpaper get --doi 10.1038/s41586-021-03819-2 --download-pdf paper.pdf --json
searchpaper get --pmcid PMC8371605 --download-xml paper.xml --json
```

PDF 解析仍是可选能力，不属于核心范围。

## 🛡️ 失败模式与信号边界

| 主题 | 行为 |
|---|---|
| 源降级 | 公共 API 可能失败；optional 源 warning 后继续 |
| 必需源 | `--require pubmed` 或 `--source-mode pubmed:required` 失败时返回 exit code 1 |
| 优先源 | `source:preferred` 给出更明显 warning，但不让整体失败 |
| 生物医学信号 | PubTator3/共现信号不是因果证据 |
| 证据评估 | 超出范围；SearchPaper 返回记录、provenance 和 signals |

## 🗂️ 缓存、隐私与项目模式

- 默认缓存：`~/.cache/searchpaper/cache.db`
- 绕过缓存：`searchpaper search "query" --no-cache --json`
- 项目模式：

```bash
searchpaper init
searchpaper search "HCC TACE PD-1" --json --save
searchpaper project traces
searchpaper project export <trace_id> --format bibtex
```

缓存可能包含原始 API 响应和查询标识符，请按敏感数据妥善保管。

## 🧪 开发

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check .
uv run ruff format .
```

CI 应使用 fixture-backed tests。Live public API 可用于人工检查，但不应成为常规验证要求。

## 📜 许可证

MIT
