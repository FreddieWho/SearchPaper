# paperSearch 中文文档

[English README](README.md)

**paperSearch** 是一个本地_stdio_ MCP 服务器，让 AI 编程助手（Claude Code、OpenCode、Codex）能够结构化、可引用地检索学术文献。它把 **Semantic Scholar**（论文搜索、引用、参考文献、推荐）和 **PubTator3**（生物医学实体标准化、实体关系、PMID 证据）封装成一个可缓存、可复现的工具集。

适用场景：文献综述自动化、系统综述支持、引用图分析、基因-药物-疾病关系挖掘、生物医学证据检索、论文推荐、以及在 agent 工作流中进行研究问题回答。

关键词：MCP server、学术搜索、论文检索、Semantic Scholar、PubTator3、PubMed、引用图、生物医学自然语言处理、实体关系、文献综述、生物信息学、肿瘤免疫、单细胞、免疫治疗、研究助手、AI agent 工具。

---

## 它能做什么

- 跨 Semantic Scholar 搜索学术论文，支持年份、期刊、引用数、开放获取和排序过滤。
- 把生物医学实体解析为 PubTator3 标准 ID：`@GENE_JAK1`、`@CHEMICAL_Pembrolizumab`、`@DISEASE_Neoplasms`。
- 挖掘实体关系，如 `treat`、`inhibit`、`cause`、`associate`、`interact`，并链接回 PubMed 证据。
- 遍历引用图（被引用/参考文献），并基于示例论文进行推荐。
- 把结果缓存在本地 SQLite 中，重复查询更快、更可复现。

---

## 功能

### Semantic Scholar 工具
- `s2_search_papers` – 通用论文搜索，支持年份、期刊、引用数、排序等过滤
- `s2_get_paper` – 单篇论文元数据（支持 S2 paperId、DOI、PMID、arXiv）
- `s2_batch_get_papers` – 批量查询元数据（最多 100 篇）
- `s2_get_citations` / `s2_get_references` – 引用图谱遍历
- `s2_recommend_papers` – 基于正/负例论文推荐

### PubTator3 工具
- `pubtator_find_entity` – 生物医学实体标准化（如 `@GENE_JAK1`、`@CHEMICAL_Pembrolizumab`）
- `pubtator_find_relations` – 实体间生物医学关系及 PMID 证据计数
- `pubtator_search` – 自由文本或关系查询

### 组合工具
- `biomed_relation_evidence` – 从普通名称解析到实体 ID、关系及 PMID 证据
- `paper_enrich_with_pubtator` – 用 PubTator 注释丰富 Semantic Scholar 论文
- `research_query` – 统一文献搜索，可选 PubTator 增强

---

## 快速开始

```bash
git clone <repo-url> ~/Publish/paperSearch
cd ~/Publish/paperSearch
uv sync --extra dev
```

创建本地配置文件：

```bash
mkdir -p ~/.config/paperSearch
cp config.example.json ~/.config/paperSearch/config.json
# 编辑 ~/.config/paperSearch/config.json，填入你的 Semantic Scholar API key
```

运行冒烟测试：

```bash
uv run python scripts/smoke_test.py
```

---

## 配置

paperSearch 先读取用户级 JSON 配置文件，再用环境变量覆盖。

### 配置文件（推荐）

路径：`~/.config/paperSearch/config.json`

```json
{
  "semantic_scholar_api_key": "YOUR_SEMANTIC_SCHOLAR_API_KEY",
  "cache_path": "/tmp/paper_search_cache.db"
}
```

| 配置项 | 是否必填 | 默认值 | 说明 |
|---|---|---|---|
| `semantic_scholar_api_key` | 建议填写 | — | 见下方 [API Token 说明](#api-token-说明) |
| `cache_path` | 否 | `/tmp/paper_search_cache.db` | 本地 SQLite 缓存文件路径 |

### 环境变量

如果设置了以下环境变量，会覆盖配置文件中的值：

| 变量 | 说明 |
|---|---|
| `SEMANTIC_SCHOLAR_API_KEY` | Semantic Scholar API key |
| `PAPER_SEARCH_CACHE` | SQLite 缓存文件路径 |

仓库里提供了 `.env.example` 模板，供喜欢 dotenv 方式的用户参考。**请勿提交 `.env` 或 `config.json`。** 它们已被 `.gitignore` 忽略。

---

## API Token 说明

### Semantic Scholar API Key

- **用途：** 认证 Semantic Scholar Academic Graph API 请求。使用 key 可以比匿名访问获得更高的速率限制。
- **来源：** https://www.semanticscholar.org/product/api
- **是否必填：** 否。没有 key 也能运行，但会受到更严格的匿名速率限制。
- **填写方式：** 写入 `~/.config/paperSearch/config.json` 的 `semantic_scholar_api_key`，或导出环境变量 `SEMANTIC_SCHOLAR_API_KEY`。

### PubTator3

- **用途：** NCBI PubTator3 提供生物医学实体标准化、关系挖掘和文献搜索。
- **来源：** https://www.ncbi.nlm.nih.gov/research/pubtator3/
- **是否必填：** 不需要 token；PubTator3 是 NCBI 公开服务。请遵守 NCBI 的速率限制规范。

---

## Agent 安装配置

### Claude Code

编辑 `~/.claude/settings.json`（全局）或 `~/.claude.json`（项目级），在 `mcpServers` 下添加：

```json
{
  "mcpServers": {
    "paperSearch": {
      "command": "uv",
      "args": [
        "--project",
        "/path/to/paperSearch",
        "run",
        "python",
        "-m",
        "paper_search.server"
      ],
      "env": {}
    }
  }
}
```

API key 从 `~/.config/paperSearch/config.json` 读取，因此不需要把 key 写进 Claude 配置。

### Codex

编辑 `~/.codex/.mcp.json`：

```json
{
  "mcpServers": {
    "paperSearch": {
      "command": "uv",
      "args": [
        "--project",
        "/path/to/paperSearch",
        "run",
        "python",
        "-m",
        "paper_search.server"
      ],
      "env": {}
    }
  }
}
```

如果你使用 `~/.codex/config.toml`：

```toml
[mcp_servers.paperSearch]
type = "stdio"
command = "uv"
args = ["--project", "/path/to/paperSearch", "run", "python", "-m", "paper_search.server"]

[mcp_servers.paperSearch.env]
```

### OpenCode

编辑 `~/.config/opencode/opencode.json`（全局）或在项目根目录创建 `opencode.json`：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "paperSearch": {
      "type": "local",
      "command": [
        "uv",
        "--project",
        "/path/to/paperSearch",
        "run",
        "python",
        "-m",
        "paper_search.server"
      ],
      "environment": {},
      "enabled": true
    }
  }
}
```

---

## 工具参考

所有工具都返回统一的响应信封：

```json
{
  "source": "semantic_scholar|pubtator3|composite",
  "query": ...,
  "retrieved_at": "2026-06-30T12:00:00Z",
  "cache_key": "sha256...",
  "from_cache": false,
  "raw_ids": [...],
  "items": [...],
  "warnings": []
}
```

### Semantic Scholar

| 工具 | 说明 |
|---|---|
| `s2_search_papers` | 通用论文搜索 |
| `s2_get_paper` | 单篇论文详情 |
| `s2_batch_get_papers` | 批量查询元数据（最多 100 篇） |
| `s2_get_citations` | 查询引用给定论文的文献 |
| `s2_get_references` | 查询给定论文的参考文献 |
| `s2_recommend_papers` | 基于示例论文推荐 |

### PubTator3

| 工具 | 说明 |
|---|---|
| `pubtator_find_entity` | 实体自动补全/标准化 |
| `pubtator_find_relations` | 实体间生物医学关系 |
| `pubtator_search` | 文献/PMID 搜索 |

### 组合工具

| 工具 | 说明 |
|---|---|
| `biomed_relation_evidence` | 名称 → 实体 ID → 关系 → PMID 证据 |
| `paper_enrich_with_pubtator` | 用 PubTator 注释丰富论文 |
| `research_query` | 统一搜索，可选 PubTator 增强 |

---

## 为什么选择 paperSearch？

大多数大模型文献检索只是浅层网页查询。paperSearch 让 agent 能够：

- **结构化元数据**：DOI、PMID、引用数、期刊、作者、开放获取 PDF。
- **实体级推理**：来自 PubTator3 的基因、化合物、疾病、变异。
- **可引用证据**：每个关系都由 PubMed PMID 支持。
- **本地缓存**：SQLite TTL 缓存减少 API 调用，结果更可复现。
- **原生 agent 支持**：stdio MCP 让它开箱即用，支持 Claude Code、OpenCode、Codex 及任何其他 MCP 客户端。

---

## 开发

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest -q
uv run python scripts/smoke_test.py
```

---

## 许可证

MIT
