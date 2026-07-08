# SearchPaper MCP 实际功能压测报告

**运行时间**：2026-07-08 06:51:37 UTC  
**压测脚本**：`scripts/benchmark_mcp.py`  
**原始数据**：`reports/mcp_benchmark_full.json`  
**总调用次数**：115  
**整体成功率**：98.26%（113/115）  
**整体平均延迟**：4806 ms  

## 1. 压测方法

使用 Python `mcp` SDK 的 `stdio_client` 启动 `searchpaper serve --mcp`，通过 `ClientSession` 调用全部 11 个 MCP 工具。压测覆盖：

- 单工具冒烟测试（11 次）
- 重复搜索缓存测试（20 次）
- 多查询搜索（10 次）
- 单源/多源降级测试（5 次）
- 并发调用（5 并发 × 3 轮）
- 连续长会话（50 次混合调用）
- 异常输入测试（4 次）

压测使用独立的临时缓存文件，避免污染默认缓存。

## 2. 关键结果

| 指标 | 数值 |
|---|---|
| 总调用 | 115 |
| 成功 | 113 |
| 失败 | 2 |
| 整体成功率 | 98.26% |
| 平均延迟 | 4806 ms |
| p50 延迟 | 225 ms |
| p95 延迟 | 24519 ms |
| p99 延迟 | 34396 ms |

**延迟分布解释**：p50 极低（225 ms）主要来自缓存命中和本地计算工具；p95/p99 高主要来自首次 live API 调用和 `get_source_status`。

## 3. 各工具表现

| 工具 | 调用数 | 成功率 | 平均延迟 | 说明 |
|---|---|---|---|---|
| `search_literature` | 67 | 98.51% | 4781 ms | 缓存命中后 ~200 ms；首次调用 ~20–30 s |
| `plan_literature_search` | 13 | 100% | 6 ms | 纯本地规划，极快 |
| `get_work` | 2 | 100% | 9081 ms | 依赖 live API |
| `resolve_identifiers` | 1 | 100% | 17928 ms | 多源解析，较慢 |
| `get_source_status` | 1 | 100% | **62022 ms** | 探测全部源，非常慢 |
| `lookup_mesh` | 14 | 100% | 6439 ms | NLM MeSH API，稳定 |
| `find_related_articles` | 1 | 100% | 9512 ms | PubMed elink |
| `convert_identifiers` | 1 | **0%** | 5902 ms | **存在 bug，详见第 4 节** |
| `search_literature_signals` | 1 | 100% | 10699 ms | PubTator3 关系信号 |
| `expand_from_work` | 1 | 100% | 17877 ms | v0.2 占位实现 |
| `export_records` | 13 | 100% | 5 ms | 纯本地格式化，极快 |

## 4. 发现的问题

### 4.1 `convert_identifiers` 对 DOI 转换失败（高优先级）

- **现象**：调用 `convert_identifiers(["10.1038/s41586-021-03819-2"])` 返回 MCP tool error：
  `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`
- **根因**：`src/searchpaper/pubmed_utils.py:55` 直接调用 `resp.json()`，未处理非 200 响应或空 body。NCBI ID converter 对该 DOI 可能返回 301/空响应。
- **影响**：MCP 工具完全不可用，CLI 同样崩溃。
- **建议**：在 `convert_ids` 中检查 `resp.status_code`，对重定向/空响应返回结构化错误而非抛出异常。

### 4.2 `get_source_status` 过慢（62 秒）

- **现象**：单次 `get_source_status` 耗时 62 秒。
- **根因**：每个源适配器的 `status()` 都执行 live 探测，9 个源顺序调用，部分源（如 Semantic Scholar、PubTator3）响应慢或被限流。
- **影响**：作为 MCP 工具，60 秒+ 的调用会阻塞 agent 工作流。
- **建议**：
  - 缩短 `status()` 探测超时（如 5 秒/源）；
  - 并行探测所有源；
  - 或引入短期缓存，避免每次调用都 live 探测。

### 4.3 空 query 仍返回结果

- **现象**：`search_literature({"query": ""})` 返回 20 条 works，仅 OpenAlex 失败。
- **根因**：PubMed/Crossref 接受空 query 并返回默认结果（可能是最近收录文献）。
- **影响**：语义上不合理，agent 可能误解为成功检索。
- **建议**：在 `SearchEngine.search` 或适配器层对空 query 提前返回空结果和明确警告。

### 4.4 OpenAlex 对空 query 报错

- **现象**：空 query 时 OpenAlex 出现 `NoneType' object has no attribute 'get'`。
- **根因**：`src/searchpaper/sources/openalex.py` 未处理 API 返回空/异常结构。
- **建议**：在解析响应前增加空值检查。

### 4.5 `expand_from_work` 是占位实现

- **现象**：工具返回 warning `"expand_from_work by ['citations'] is a v0.2 extension point; returning resolved work."`
- **影响**：功能名不副实，agent 可能期望引用/推荐扩展。
- **建议**：v0.3 按路线图实现真正的 `expand_from_work`。

### 4.6 并发稳定性良好

- **现象**：5 并发 × 3 轮全部成功，未触发明显限流或崩溃。
- **说明**：SearchPaper 的降级策略和缓存机制在并发场景下表现稳定。

## 5. 性能亮点

- **缓存效果显著**：重复搜索从首次 ~20 s 降至 ~200 ms，提升约 100 倍。
- **本地工具极快**：`plan_literature_search`、`export_records` 稳定在 10 ms 以内。
- **多源部分成功稳定**：单源失败不阻塞整体返回，符合设计预期。
- **长会话稳定**：50 次混合调用后无失败率上升或 server 崩溃。

## 6. 改进建议（按优先级）

1. **修复 `convert_identifiers`**：处理非 JSON/空响应，返回结构化错误。
2. **优化 `get_source_status`**：并行探测、缩短超时、加缓存。
3. **校验空 query**：在引擎层拒绝空 query，避免无意义调用。
4. **增强 OpenAlex 鲁棒性**：对异常/空响应做空值保护。
5. **实现真正的 `expand_from_work`**：按 v0.3 路线图扩展引用/推荐功能。
6. **增加 MCP 层输入校验错误处理**：当前 Pydantic 验证错误直接以 MCP tool error 暴露，可返回更友好的 envelope 错误。

## 7. 结论

SearchPaper MCP server 在 live API 环境下整体可用，核心搜索、信号、导出功能稳定，缓存机制有效。但 `convert_identifiers` 存在 bug，`get_source_status` 性能不佳，空 query 和 OpenAlex 异常需要加固。修复上述问题后，MCP 工具面可达到生产可用水平。
