# SearchPaper 中文文档

[English README](README.md)

**SearchPaper** 是一个面向 agent 辅助研究的文献检索基础设施层。它跨多个开放学术源搜索文献、规范化标识符、保守合并重复记录、保留来源出处，并导出可追踪的结果。

它不是完整的研究 agent、系统综述 agent、证据评估引擎、PDF 解析器，也不是 Zotero 替代品。

支持源：PubMed、Crossref、OpenAlex、Europe PMC、Semantic Scholar 和 PubTator3（生物医学信号）。核心工作流默认**无需 API 密钥**即可使用。

---

## 快速开始

```bash
git clone <repo-url> ~/Publish/paperSearch
cd ~/Publish/paperSearch
uv sync --extra dev
uv run pytest -q
```

搜索：

```bash
searchpaper search "HCC TACE PD-1" --json
```

解析 DOI：

```bash
searchpaper resolve --doi 10.1038/s41586-021-03819-2 --json
```

查看源状态：

```bash
searchpaper sources status --json
searchpaper doctor
```

---

## 配置

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
| `SEMANTIC_SCHOLAR_API_KEY` | `semantic_scholar_api_key` | 可选 S2 密钥 |
| `CROSSREF_EMAIL` | `crossref_email` | 礼貌池邮箱 |
| `OPENALLEX_EMAIL` | `openalex_email` | 礼貌池邮箱 |
| `NCBI_API_KEY` | `ncbi_api_key` | 可选 NCBI 密钥 |

---

## CLI 命令

| 命令 | 说明 |
|---|---|
| `searchpaper search "query" --json` | 搜索文献 |
| `searchpaper get --pmid 12345 --json` | 按标识符获取作品 |
| `searchpaper resolve --doi 10.xxx --json` | 跨源解析标识符 |
| `searchpaper sources status --json` | 源健康状态 |
| `searchpaper cache stats` | 缓存统计 |
| `searchpaper cache clear` | 清空缓存 |
| `searchpaper doctor` | 诊断 |
| `searchpaper capabilities --json` | 能力报告 |
| `searchpaper serve --mcp` | 启动 MCP 服务器（stdio） |
| `searchpaper signals "PDCD1" --json` | 生物医学信号 |
| `searchpaper export results.json --format bibtex` | 导出结果 |
| `searchpaper install --target opencode` | 安装 agent 集成 |

---

## MCP 工具

- `search_literature`
- `get_work`
- `resolve_identifiers`
- `get_source_status`
- `search_literature_signals`
- `expand_from_work`
- `export_records`

默认不暴露源特定的 MCP 工具。

---

## Agent 集成

### OpenCode

```bash
searchpaper install --target opencode
```

### Codex / Claude

```bash
searchpaper install --target codex
searchpaper install --target claude
searchpaper install --target all
```

生成 MCP 配置片段和说明文件后，请在 agent 设置中启用 `searchpaper` MCP 服务器。

---

## 信号级别

SearchPaper 返回带有明确级别的文献信号：

1. **书目信号** — 标题、期刊、年份、作者、引用、来源命中。
2. **摘要信号** — 标题/摘要/关键词/MeSH/概念。
3. ** curated 或提取关系 ** — PubTator3、MeSH 类关系、源提供的实体关系。
4. **全文锚点** — 留给未来 OA/PMC 支持。
5. **评估证据** — 超出 SearchPaper 范围。

信号不是已评估的结论。不要把 PubTator 共现或关系报告为因果证明。

---

## 源降级

公共 API 可能不稳定。当某个源失败时，SearchPaper 返回带有明确警告和追踪条目的部分结果。降级源不会导致整个搜索失败。使用 `searchpaper sources status` 查看当前源健康状态。

---

## 缓存与隐私

- 默认缓存位于 `~/.cache/searchpaper/cache.db`。
- 搜索时可用 `--no-cache` 绕过缓存。
- 缓存包含原始 API 响应和查询标识符，请妥善保管。

---

## 无需 live API 的测试

CI 仅运行基于 fixture 的测试，live API 测试默认跳过：

```bash
uv run pytest -q
```

---

## 开发

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format .
uv run pytest -q
```

---

## 许可证

MIT
