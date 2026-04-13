## ADDED Requirements

### Requirement: Query Rewrite 机制
系统应在 RAG 检索前对用户 query 进行改写，融入对话历史上下文，消除代词歧义。

#### Scenario: 代词消解
- **WHEN** 用户 query 包含代词（"它"、"这个"、"那个"）
- **THEN** 系统结合窗口内历史记录，将代词替换为具体名词

#### Scenario: 省略补全
- **WHEN** 用户 query 有省略（如"支持哪些格式？"缺少主语）
- **THEN** 系统从历史中推断省略的内容，补全 query

#### Scenario: 改写失败降级
- **WHEN** Query Rewrite 调用失败或超时
- **THEN** 系统降级为使用原始 query 进行检索

#### Scenario: 多轮对话上下文
- **WHEN** 用户连续多轮提问同一主题
- **THEN** 改写后的 query 应保持主题连贯性

### Requirement: Query Rewrite 配置
系统应支持配置 Query Rewrite 的行为参数。

#### Scenario: Rewrite 开关配置
- **WHEN** 系统在 `app/config.py` 中配置 `CHAT_MEMORY_QUERY_REWRITE_ENABLED`
- **THEN** Query Rewrite 功能使用该配置值，默认为 true

#### Scenario: Rewrite 超时配置
- **WHEN** 系统在 `app/config.py` 中配置 `CHAT_MEMORY_QUERY_REWRITE_TIMEOUT_SECONDS`
- **THEN** Rewrite 调用超时使用该配置值，默认为 5 秒

#### Scenario: Rewrite 模型配置
- **WHEN** 系统在 `app/config.py` 中配置 `CHAT_MEMORY_QUERY_REWRITE_MODEL`
- **THEN** Rewrite 使用的模型为该配置值，默认为轻量级模型
