## ADDED Requirements

### Requirement: 反馈提交 API
系统 SHALL 提供 `POST /api/feedback` 端点，接受 JSON body 包含 `message_id`、`conversation_id`、`type`（positive/negative）。

#### Scenario: 提交正向反馈
- **WHEN** 客户端 POST `{"message_id":1,"conversation_id":1,"type":"positive"}`
- **THEN** MUST 创建或更新反馈记录
- **THEN** MUST 返回 `{"success":true}`

#### Scenario: 重复提交覆盖
- **WHEN** 同一用户对同一消息再次提交反馈
- **THEN** MUST 更新现有记录而非新建
- **THEN** MUST 返回 `{"success":true,"updated":true}`

### Requirement: 检索日志查询 API
系统 SHALL 提供 `GET /api/rag-logs` 端点，支持分页（`page`、`per_page`）、筛选（`route_type`、`min_similarity`）、搜索（`search`）。

#### Scenario: 基本日志查询
- **WHEN** 客户端 GET `/api/rag-logs?page=1&per_page=20`
- **THEN** MUST 返回 `{"success":true,"items":[...],"pagination":{...},"stats":{...}}`
- **THEN** `stats` MUST 包含 `total_queries`、`avg_similarity`、`avg_judge_score`、`positive_feedback_rate`

#### Scenario: 日志详情查询
- **WHEN** 客户端 GET `/api/rag-logs/<id>`
- **THEN** MUST 返回该条日志的完整信息，包含 `results_json` 完整检索结果和关联的用户反馈

### Requirement: LLM-as-Judge API
系统 SHALL 提供 `POST /api/rag-logs/<id>/judge` 端点，触发对该条检索日志的 LLM-as-Judge 评估。

#### Scenario: 触发评估
- **WHEN** 客户端 POST `/api/rag-logs/1/judge`
- **THEN** 系统 MUST 异步调用 LLM 对检索结果进行评估
- **THEN** MUST 返回 `{"success":true,"judge_score":{...},"judge_reason":"..."}`

#### Scenario: 重复评估
- **WHEN** 对已评估的日志再次 POST judge
- **THEN** MUST 覆盖旧评分，返回新的评估结果

### Requirement: Dashboard 统计 API
系统 SHALL 提供 `GET /api/rag-logs/stats` 端点，返回 Dashboard 统计卡片所需数据。

#### Scenario: 统计数据
- **WHEN** 客户端 GET `/api/rag-logs/stats`
- **THEN** MUST 返回 `{"success":true,"stats":{"total_queries":...,"avg_similarity":...,"avg_judge_score":...,"positive_rate":...,"today_queries":...}}`
