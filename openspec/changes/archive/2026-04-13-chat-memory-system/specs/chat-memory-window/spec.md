## ADDED Requirements

### Requirement: 短期记忆窗口管理
系统应保留最近 N 条（默认 5 条）完整聊天记录，支持按会话 ID 和时间戳查询窗口内记录。

#### Scenario: 获取窗口内聊天记录
- **WHEN** 用户请求获取某会话的聊天记录
- **THEN** 系统返回最近 5 条记录，按时间戳降序排列

#### Scenario: 窗口大小可配置
- **WHEN** 系统在 `app/config.py` 中配置 `CHAT_MEMORY_WINDOW_SIZE`
- **THEN** 窗口大小使用该配置值，默认为 5

#### Scenario: 新记录加入窗口
- **WHEN** 新聊天记录产生
- **THEN** 记录被添加到窗口，若超出窗口大小则将最旧记录标记为"待压缩"

### Requirement: 窗口检索接口
系统应提供 REST API 端点，支持按会话 ID 检索窗口内的完整聊天记录。

#### Scenario: 成功检索窗口记录
- **WHEN** 客户端发送 `GET /api/chat-memory/{session_id}/window` 请求
- **THEN** 系统返回 JSON 格式的窗口内聊天记录列表

#### Scenario: 会话不存在
- **WHEN** 请求的会话 ID 不存在
- **THEN** 系统返回 404 错误
