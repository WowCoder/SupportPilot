## MODIFIED Requirements

### Requirement: 短期记忆窗口管理
系统应保留最近 N 条（默认 5 条）完整聊天记录，支持按会话 ID 和时间戳查询窗口内记录。窗口管理需支持对话轮次计数和工单状态追踪。

#### Scenario: 获取窗口内聊天记录
- **WHEN** 用户请求获取某会话的聊天记录
- **THEN** 系统返回最近 5 条记录，按时间戳降序排列，包含当前轮次计数

#### Scenario: 窗口大小可配置
- **WHEN** 系统在 `app/config.py` 中配置 `CHAT_MEMORY_WINDOW_SIZE`
- **THEN** 窗口大小使用该配置值，默认为 5

#### Scenario: 新记录加入窗口
- **WHEN** 新聊天记录产生
- **THEN** 记录被添加到窗口，若超出窗口大小则将最旧记录标记为"待压缩"，轮次计数 +1

#### Scenario: 轮次达到阈值触发人工介入
- **WHEN** 对话轮次达到 3 轮（可配置）
- **THEN** 系统标记该会话为"可人工介入"状态，前端显示人工介入按钮

### Requirement: 窗口检索接口
系统应提供 REST API 端点，支持按会话 ID 检索窗口内的完整聊天记录，并返回工单状态信息。

#### Scenario: 成功检索窗口记录
- **WHEN** 客户端发送 `GET /api/chat-memory/{session_id}/window` 请求
- **THEN** 系统返回 JSON 格式的窗口内聊天记录列表，包含轮次计数和工单状态

#### Scenario: 会话不存在
- **WHEN** 请求的会话 ID 不存在
- **THEN** 系统返回 404 错误

#### Scenario: 获取工单状态
- **WHEN** 客户端发送 `GET /api/ticket/{session_id}/status` 请求
- **THEN** 系统返回工单状态（开放/待人工处理/已关闭）和轮次计数

## ADDED Requirements

### Requirement: 工单状态追踪
系统应为每个会话 ID 关联工单状态，支持标记为"开放"、"待人工处理"、"已关闭"。

#### Scenario: 新建会话自动创建工单
- **WHEN** 用户首次发送消息创建新会话
- **THEN** 系统自动创建工单记录，状态为"开放"

#### Scenario: 用户点击人工介入
- **WHEN** 用户点击"需要人工介入"按钮
- **THEN** 系统更新工单状态为"待人工处理"

#### Scenario: 用户关闭工单
- **WHEN** 用户点击"关闭工单"按钮并确认
- **THEN** 系统更新工单状态为"已关闭"，记录关闭时间

#### Scenario: 工单关闭后禁止 AI 回复
- **WHEN** 工单状态为"已关闭"
- **THEN** 系统禁止 AI 对该会话的新消息进行回复，提示用户工单已关闭

### Requirement: 关单 FAQ 生成触发
系统应在技术支持关闭工单时提供 FAQ 生成选项，触发 FAQ 审核工作流。

#### Scenario: 技术支持选择生成 FAQ
- **WHEN** 技术支持在关单界面勾选"生成 FAQ"
- **THEN** 系统调用 AI 基于会话内容生成 FAQ 草稿

#### Scenario: FAQ 草稿提交审核
- **WHEN** FAQ 生成成功
- **THEN** 系统将 FAQ 草稿状态设为"待审核"，等待技术支持确认
