## ADDED Requirements

### Requirement: 批量异步压缩机制
系统应对超出窗口的记录采用批量压缩策略，而非逐条实时压缩。

#### Scenario: 标记待压缩记录
- **WHEN** 新聊天记录产生且窗口已达上限
- **THEN** 系统将最旧的记录标记为"pending_compression"，不立即调用 LLM

#### Scenario: 批量压缩触发条件
- **WHEN** 待压缩记录累积到 5 条 或 会话空闲超过 30 秒
- **THEN** 系统触发批量压缩任务，将待压缩记录一起发送给 LLM 生成摘要

#### Scenario: 摘要压缩率目标
- **WHEN** 生成摘要时
- **THEN** 摘要长度应为原始记录的 1/10（目标压缩率 10:1）

#### Scenario: 保留原始记录
- **WHEN** 生成摘要后
- **THEN** 原始聊天记录不被删除，摘要作为补充字段存储

#### Scenario: 摘要内容完整性
- **WHEN** 生成摘要时
- **THEN** 摘要应保留关键信息：客户问题、解决方案、待办事项

### Requirement: 异步任务队列
系统应支持后台异步处理压缩任务，不阻塞用户发送消息。

#### Scenario: 异步压缩不阻塞
- **WHEN** 用户发送新消息时
- **THEN** 消息立即保存并返回，压缩任务在后台异步执行

#### Scenario: 队列持久化
- **WHEN** 服务重启时
- **THEN** 待压缩队列不丢失，重启后继续处理

#### Scenario: 兜底机制触发压缩
- **WHEN** 待压缩记录超过 2 分钟未处理
- **THEN** 系统强制触发批量压缩，无论队列中有多少条记录

### Requirement: 摘要检索接口
系统应提供 REST API 端点，支持检索历史摘要作为上下文补充。

#### Scenario: 成功检索摘要
- **WHEN** 客户端发送 `GET /api/chat-memory/{session_id}/summary` 请求
- **THEN** 系统返回该会话的所有历史摘要列表

#### Scenario: 按时间范围检索摘要
- **WHEN** 客户端发送 `GET /api/chat-memory/{session_id}/summary?start_date=X&end_date=Y` 请求
- **THEN** 系统返回指定时间范围内的摘要

### Requirement: 窗口大小配置
系统应支持配置短期记忆窗口的大小。

#### Scenario: 窗口大小可配置
- **WHEN** 系统在 `app/config.py` 中配置 `CHAT_MEMORY_WINDOW_SIZE`
- **THEN** 窗口大小使用该配置值，默认为 5

#### Scenario: 批量压缩阈值配置
- **WHEN** 系统在 `app/config.py` 中配置 `CHAT_MEMORY_COMPRESSION_BATCH_SIZE`
- **THEN** 批量压缩触发阈值使用该配置值，默认为 5 条

#### Scenario: 空闲触发阈值配置
- **WHEN** 系统在 `app/config.py` 中配置 `CHAT_MEMORY_IDLE_THRESHOLD_SECONDS`
- **THEN** 空闲触发阈值使用该配置值，默认为 30 秒

#### Scenario: 兜底时间阈值配置
- **WHEN** 系统在 `app/config.py` 中配置 `CHAT_MEMORY_COMPRESSION_MAX_DELAY_SECONDS`
- **THEN** 兜底触发阈值使用该配置值，默认为 120 秒（2 分钟）

#### Scenario: 队列上限保护
- **WHEN** 待压缩队列超过 10 条
- **THEN** 系统降级为实时压缩模式，避免队列无限堆积
