# SearchPaper Patch Roadmap

**版本**：searchpaper 0.5.0
**目标**：基于 `dev/02/03/04` spec 与 `nature-academic-search` 对标分析，把当前缺口按重要程度和工程相关性整理为可执行的 patch 路线。
**对应报告**：`reports/spec_and_coverage_report.md`

---

## 优先级定义

| 优先级 | 含义 |
|--------|------|
| P0 | 阻塞 spec 合规或影响核心行为；应尽快补齐 |
| P1 | 提升 spec 完整度或 agent 体验；建议下一版本完成 |
| P2 | 扩展工作流覆盖；可作为后续迭代 |
| P3 | 质量、细节、文档打磨；可择机处理 |

---

## Phase A：Foundation Completeness（spec 合规补丁）

### A1. 实现 Source Requirement Modes ✅ 已完成
- **优先级**：P0
- **依据**：`dev/03_Degradation_and_AntiLoop_Policy.md` §7
- **当前状态**：engine 对所有请求源统一按 optional 处理，失败仅记录 trace 和 warning。
- **目标**：在 `SearchEngine.search/get/resolve` 中支持 `optional` / `preferred` / `required` 三种模式；单个 required 源失败时命令返回非零退出码和结构化错误。
- **工程改动**：
  1. ✅ 新增 `SourceMode` 枚举（`optional` / `preferred` / `required`）和 `SourceRequiredError` 异常。
  2. ✅ `SearchFilters` 增加 `source_modes: dict[str, SourceMode]`；`engine.py` 的 `search/get/resolve/expand/context` 均支持 `source_modes` 参数。
  3. ✅ required 源失败时抛出 `SourceRequiredError`，携带部分结果 envelope；preferred 源失败时在 warnings 中前置 louder warning。
  4. ✅ CLI 为 `search/get/resolve/expand/context` 增加 `--require` 和 `--source-mode` 选项；捕获异常后输出 JSON 并以退出码 1 结束。
  5. ✅ MCP `search_literature` / `get_work` / `resolve_identifiers` / `expand_from_work` 增加 `source_modes` 参数字符串映射；失败时返回 `object_type: error` 的结构化响应。
  6. ✅ Crossref / OpenAlex adapter 对 HTTP >= 400 和非 JSON 响应改为抛出异常，使 engine 能正确标记 source failed。
  7. ✅ 新增 `tests/test_source_modes.py`，并在 `tests/test_cli.py`、`tests/test_mcp.py` 中补充场景测试。
- **验证**：`uv run python -m pytest -q` 113 passed；`ruff check/format` clean。

### A2. 补全 `searchpaper batch` 命令 ✅ 已完成
- **优先级**：P1
- **依据**：`dev/02_Goal_Mode_Execution_Prompt.md` Priority 6 Stretch
- **当前状态**：未实现。
- **目标**：支持 JSONL 或文本输入批量搜索/解析/导出。
- **工程改动**：
  1. ✅ 新增 `src/searchpaper/batch.py`，实现 `process_batch()`：逐行解析输入，支持 `query` 搜索和 `doi`/`pmid`/`pmcid`/`arxiv` 解析。
  2. ✅ CLI 新增 `searchpaper batch <input.jsonl> --format json|jsonl|bibtex|ris|nbib|enw|markdown|zotero|obsidian --output <file>`。
  3. ✅ 支持 `--sources`、`--require`、`--source-mode`、`--limit`、`--year` 等选项。
  4. ✅ 复用 `SearchEngine.search`/`resolve`；单个 item 失败（包括 required source 失败）不影响后续 item，最终输出聚合 summary 与 warnings。
  5. ✅ `capabilities --json` 的 `cli_commands` 已加入 `batch`。
  6. ✅ 新增 `tests/test_batch.py`，覆盖 json/jsonl/bibtex 输出及 CLI 调用。
- **验证**：`uv run python -m pytest -q` 117 passed；`ruff check/format` clean。

### A3. 修复 managed state 字段缺失 ✅ 已完成
- **优先级**：P1
- **依据**：`dev/04_Agent_Integration_and_Skill_Spec.md` §8
- **当前状态**：`integrations.json` 记录 `modes`、`scope`、`installed_at`、`managed_files`，但缺少 `config_path`。
- **目标**：与 spec 示例结构对齐。
- **工程改动**：
  1. 在 `src/searchpaper/integrations/manager.py` 的 install/migrate 中，为每个 target 记录 `config_path`。
  2. 各 target module 提供 `config_path()` 返回主配置文件路径。
  3. 更新 `tests/test_integration.py` 断言。

---

## Phase B：Agent Integration Hardening

### B1. 实现 OpenCode Custom Tool Wrapper ✅ 已完成
- **优先级**：P1
- **依据**：`dev/04_Agent_Integration_and_Skill_Spec.md` §13
- **当前状态**：仅有 MCP 配置和 skill 安装，无 custom tool wrapper。
- **目标**：提供一个 thin wrapper，调用 CLI 并返回解析后的 JSON，不重复核心逻辑。
- **工程改动**：
  1. 新增 `src/searchpaper/integrations/opencode_custom_tool.py`。
  2. wrapper 暴露少量高频命令：`search`、`get`、`resolve`、`signals`。
  3. 在 OpenCode install 时可选生成 custom tool 文件到 `~/.config/opencode/tools/searchpaper.json`（或对应位置）。
  4. 增加 `--mode custom_tool` 支持，使 `searchpaper install --target opencode --mode custom_tool` 生效。
  5. 新增测试验证 wrapper 输出符合 CLI schema。

### B2. Codex / Claude 集成深度补齐 ✅ 已完成
- **优先级**：P2
- **依据**：`dev/04_Agent_Integration_and_Skill_Spec.md` §6、§7
- **当前状态**：Codex/Claude 仅生成独立 snippet/instructions，未写入用户主 config（这是安全设计，但 agent 体验较弱）。
- **目标**：在保持安全原则下，提供更完整的 scaffold：
  - 自动检测 Codex `settings.json` / Claude `mcp.json` 是否存在。
  - 提供 marker-delimited 的 config 注入选项（默认 dry-run）。
  - `integrate doctor` 对 Codex/Claude 给出“如何手动 merge”的清晰指引。
- **工程改动**：
  1. `codex.py` / `claude.py` 增加 `can_modify_user_config()` 和 `inject_config_snippet(dry_run=True)`。
  2. `manager.py` 的 doctor 输出包含“manual merge instructions”。

---

## Phase C：Workflow Coverage Expansion（对标 nature-academic-search）

### C1. 引用验证工作流（Citation Verification） ✅ 已完成
- **优先级**：P2
- **依据**：nature `references/workflows/wf2-citation-verification.md`
- **当前状态**：完全未实现；无 citation parser、无文档导入、无 verified/mismatch 分类。
- **目标**：实现基础引用验证流水线。
- **工程改动**：
  1. 新增 `src/searchpaper/citation_parser.py`：支持从 `.txt` 提取引用行；可选支持 `.docx`（需 `python-docx`）和 `.tex`（正则提取 `\cite` / bibliography）。
  2. 新增 `searchpaper references verify <document> --format docx|tex|txt`。
  3. 对每条引用执行 `resolve_identifiers` 或 `search_literature`，分类为 `verified` / `mismatch` / `not_found` / `suspicious` / `manual_needed`。
  4. 输出 summary + detail table（JSON/CSV/Markdown）。
  5. 新增测试与 fixtures。

### C2. refs.txt 增强 ✅ 已完成
- **优先级**：P2
- **依据**：nature `references/workflows/wf4-citation-file-mgmt.md`
- **当前状态**：`src/searchpaper/reference_convert.py` 仅支持 `DOI:`、`PMID:`、`ARXIV:` 行。
- **目标**：支持 `QUERY:` 和 `AUTHOR:... TITLE:...` 行。
- **工程改动**：
  1. `parse_refs_file()` 识别 `QUERY:` 行，调用 `SearchEngine.search` 取第一条结果。
  2. 识别 `AUTHOR:` + `TITLE:` 组合，构造搜索查询。
  3. 对解析出的 work 进行 `resolve` 或 `get` 以补全元数据。
  4. 更新 `tests/test_reference_convert.py`（如存在）或新增测试。

### C3. APA / MLA 引用格式化 ✅ 已完成
- **优先级**：P2
- **依据**：nature `references/workflows/wf5-reference-mgmt.md` 5d
- **当前状态**：`export.py` 支持 bibtex/ris/nbib/enw/markdown/zotero/obsidian，缺 APA/MLA。
- **工程改动**：
  1. 在 `works_to_format` 中增加 `apa`、`mla` 分支。
  2. 实现 `work_to_apa()` / `work_to_mla()`，处理 author/year/title/venue/volume/pages/doi。
  3. 更新 `capabilities` 输出和 README。

### C4. Full-text 访问层扩展（仅报告/下载元数据） ✅ 已完成
- **优先级**：P2
- **依据**：nature WF5e、SearchPaper v0.5 已部分实现
- **当前状态**：可报告 availability 和 OA PDF URL，但不下载全文。
- **目标**：在不引入 PDF parsing 的前提下，支持“下载 OA PDF/PMC XML 到本地”作为可选操作。
- **工程改动**：
  1. CLI 增加 `searchpaper get --doi ... --download-pdf <path>` / `--download-xml <path>`。
  2. 使用 `full_text_availability.oa_pdf_url` / Europe PMC XML link 下载。
  3. 明确失败时返回 metadata-only 并标注警告。

---

## Phase D：Quality, Tests & Docs

### D1. Schema Snapshot Tests ✅ 已完成
- **优先级**：P3
- **依据**：`dev/02_Goal_Mode_Execution_Prompt.md` Testing Requirements
- **当前状态**：`tests/test_schema.py` 仅做内存序列化断言。
- **工程改动**：
  1. 引入 `syrupy` 或 `pytest-snapshot`。
  2. 对 `WorkRecord`、`SearchResult`、`SourceStatus`、`LiteratureSignal` 生成快照并版本化。

### D2. MEDLINE→RIS/BibTeX 字段映射对齐 ✅ 已完成
- **优先级**：P3
- **依据**：nature `references/ris-bibtex-format.md`
- **当前状态**：基本字段覆盖，但细节未完全对齐（如 RIS `AN  - PMID:` 前缀、页码 split、BibTeX citation key 规则）。
- **工程改动**：
  1. `work_to_ris()`：PMID 输出 `AN  - PMID:<pmid>`，页码拆分为 `SP`/`EP`。
  2. `work_to_bibtex()`：citation key 优先 `pmid<pmid>`，否则 `firstauthorYEAR`。
  3. 增加 HTML tag 清理、特殊字符转义。

### D3. Search Strategy 模板与 Combined Scoring ✅ 已完成
- **优先级**：P3
- **依据**：nature `references/search-strategy.md`
- **当前状态**：有 `planner.py` 和 source tiers，但缺少 query templates 和 combined scoring。
- **工程改动**：
  1. 在 `planner.py` 中预置 domain templates（medical/molecular/epidemiology/methods）。
  2. `rank.py` 中实现 `score = relevance * 0.5 + recency * 0.3 + citations * 0.2` 的 combined mode。
  3. `--sort combined` 暴露到 CLI/MCP。

### D4. 文档更新 ✅ 已完成
- **优先级**：P3
- **工程改动**：
  1. README 增加 `batch`、`source-mode`、`references verify` 的用法示例。
  2. `docs/workflows.md` 更新 WF2/WF4/WF5 覆盖状态。
  3. 在 `docs/limitations.md`（如不存在则新建）中明确列出未覆盖的 T3 源、中文库、APA/MLA 等。

---

## 推荐实施顺序

```text
P0  A1  Source requirement modes
P1  A2  batch 命令
P1  A3  managed state 字段补全
P1  B1  OpenCode custom tool wrapper
P2  B2  Codex/Claude 集成深度补齐
P2  C2  refs.txt 增强
P2  C3  APA/MLA 格式化
P2  C4  Full-text 下载（可选）
P2  C1  Citation verification（最大块，可单独作为一个 minor 版本）
P3  D1  Schema snapshot tests
P3  D2  RIS/BibTeX 映射细节
P3  D3  Search strategy templates
P3  D4  文档更新
```

---

## 验收标准（下一阶段）

1. `searchpaper search --require pubmed` 在 PubMed 失败时返回非零退出码和结构化错误。
2. `searchpaper batch input.jsonl --format bibtex` 可正常运行并输出。
3. `searchpaper install --target opencode` 生成的 `integrations.json` 包含 `config_path`。
4. OpenCode custom tool wrapper 文件可被 OpenCode 识别并调用 `searchpaper search`。
5. `searchpaper references convert refs.txt --format ris` 支持 `QUERY:` 和 `AUTHOR:/TITLE:` 行。
6. `searchpaper export results.json --format apa` 输出符合 APA 7 基本格式。
7. 新增/更新测试全部通过，`ruff check/format` clean。
