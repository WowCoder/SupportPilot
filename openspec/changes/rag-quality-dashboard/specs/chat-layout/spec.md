## MODIFIED Requirements

### Requirement: AI 回复下方显示反馈按钮
会话页面 SHALL 在每条 AI 消息（sender_type='ai'）下方显示 👍 和 👎 反馈按钮。用户点击后异步提交反馈到 `/api/feedback`，按钮状态高亮且支持切换。

#### Scenario: 反馈按钮渲染
- **WHEN** 会话页面包含 AI 消息
- **THEN** 每条 AI 消息下方 MUST 显示 👍 和 👎 两个按钮
- **THEN** 按钮 MUST 使用 `btn-ghost btn-xs` 样式
- **THEN** 按钮 MUST 仅在未关闭的会话中显示

#### Scenario: 用户点击反馈
- **WHEN** 用户点击 👍 按钮
- **THEN** 系统 MUST 异步 POST `/api/feedback` 记录 `type='positive'`
- **THEN** 👍 按钮 MUST 变为选中状态（accent 颜色）
- **THEN** 👎 按钮 MUST 取消选中
- **WHEN** 用户改点 👎
- **THEN** 系统 MUST POST `/api/feedback` 更新为 `type='negative'`
- **THEN** UI MUST 对应切换高亮

#### Scenario: 已关闭会话不显示反馈
- **WHEN** 会话状态为 closed
- **THEN** AI 消息下方 MUST NOT 显示反馈按钮
