## ADDED Requirements

### Requirement: AI 回复下方显示反馈按钮
会话页面 SHALL 在每条 AI 消息（sender_type='ai'）下方显示 👍 和 👎 反馈按钮，按钮小巧不干扰阅读。

#### Scenario: 反馈按钮渲染
- **WHEN** 会话页面包含 AI 消息
- **THEN** 每条 AI 消息下方 MUST 显示 👍 和 👎 两个按钮
- **THEN** 按钮 MUST 使用 `btn-ghost btn-xs` 样式

#### Scenario: 用户点 👍
- **WHEN** 用户点击 👍 按钮
- **THEN** 按钮 MUST 变为选中状态（accent 颜色高亮）
- **THEN** 系统 MUST 异步 POST `/api/feedback` 记录 `type='positive'`
- **THEN** 👎 按钮 MUST 取消选中

#### Scenario: 用户点 👎
- **WHEN** 用户点击 👎 按钮
- **THEN** 按钮 MUST 变为选中状态（红色高亮）
- **THEN** 系统 MUST 异步 POST `/api/feedback` 记录 `type='negative'`
- **THEN** 👍 按钮 MUST 取消选中

#### Scenario: 切换反馈
- **WHEN** 用户已点 👍 后改点 👎
- **THEN** 系统 MUST POST `/api/feedback` 更新为 `type='negative'`
- **THEN** UI MUST 对应更新

### Requirement: 反馈数据模型
系统 SHALL 在数据库中存储用户反馈，包含会话 ID、消息 ID、用户 ID、反馈类型、关联的检索日志 ID 和时间戳。

#### Scenario: 反馈记录结构
- **WHEN** 用户提交反馈
- **THEN** 记录 MUST 包含 `conversation_id`、`message_id`、`user_id`、`type`（positive/negative）、`retrieval_log_id`（可选）、`created_at`
