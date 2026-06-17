## ADDED Requirements

### Requirement: 检索自动记录
每次 `RAGService.retrieve()` 调用 SHALL 自动记录一条检索日志到 `rag_retrieval_logs` 表，包含查询文本、返回结果数、top-1 相似度、耗时、路由方式、完整结果 JSON。

#### Scenario: 检索日志自动记录
- **WHEN** `rag_service.retrieve()` 被调用（聊天或测试页）
- **THEN** 系统 MUST 自动插入一条日志到数据库
- **THEN** 日志 MUST 包含 `query`、`result_count`、`top1_similarity`、`duration_ms`、`route_type`（agentic/simple）、`results_json`（完整检索结果）、`created_at`

#### Scenario: 日志记录不影响检索性能
- **WHEN** 检索完成后记录日志
- **THEN** 日志插入耗时 MUST 小于 10ms
- **THEN** 日志写入失败 MUST NOT 抛出异常影响检索主流程

### Requirement: 检索结果完整存储
日志的 `results_json` 字段 SHALL 存储完整检索结果的 JSON，每条结果包含 content 全文、similarity 分数、source 来源、parent_id（如 Small-to-Big）。

#### Scenario: results_json 内容
- **WHEN** 检索返回 3 条结果
- **THEN** `results_json` MUST 是包含 3 个对象的 JSON 数组
- **THEN** 每个对象 MUST 包含 `content`（全文）、`similarity`、`source`、`parent_id`（可选）

### Requirement: 检索日志查询
系统 SHALL 提供按时间倒序、分页的检索日志列表，支持按路由方式、最低分数筛选。

#### Scenario: Dashboard 日志列表
- **WHEN** 技术支持访问 RAG Dashboard
- **THEN** MUST 显示最近 20 条检索日志
- **THEN** 每条日志 MUST 显示查询文本（截断 80 字符）、结果数、top-1 相似度（颜色区分 >=0.7 绿 / 0.4-0.7 橙 / <0.4 红）、路由方式、耗时、LLM-Judge 评分（如已评估）、时间
