## ADDED Requirements

### Requirement: User Dashboard 页面布局
用户仪表盘 SHALL 使用 topnav + page-content 布局，包含 section-header（欢迎标题 + 角色 badge + 创建会话按钮）、stats-grid（3 个统计卡片）、创建新会话卡片、我的会话列表。

#### Scenario: 页面结构
- **WHEN** 普通用户登录后访问首页
- **THEN** 页面 MUST 显示 "欢迎，<username>!" 标题
- **THEN** 页面 MUST 显示角色 badge（"用户" 或 "技术支持"）
- **THEN** 页面 MUST 显示 "创建会话" 按钮

### Requirement: 统计卡片
User Dashboard SHALL 显示 3 个统计卡片：会话总数、进行中会话、需关注会话，数值从后端 `conversations` 数据计算。

#### Scenario: 统计卡片渲染
- **WHEN** User Dashboard 页面加载
- **THEN** MUST 显示 3 张卡片：会话总数、进行中（active）、需关注（needs_attention）
- **THEN** 每张卡片 MUST 包含图标、数值、标签

### Requirement: 创建新会话卡片
Dashboard SHALL 包含 "开始新的会话" 卡片，内含说明文字和 "创建会话" 按钮（POST 表单 + CSRF token）。

#### Scenario: 创建会话
- **WHEN** 用户点击 "创建会话" 按钮
- **THEN** MUST POST 到 `conversation.create_conversation` 并创建新会话

### Requirement: 我的会话列表
Dashboard SHALL 显示用户的所有会话列表，每条显示会话 ID、状态 badge（颜色区分）、创建时间。无会话时显示空状态。

#### Scenario: 会话列表渲染
- **WHEN** 用户有历史会话
- **THEN** 每行 MUST 显示会话 ID、状态 badge（active=绿色、needs_attention=红色、closed=灰色）、创建时间

#### Scenario: 空会话列表
- **WHEN** 用户没有会话
- **THEN** MUST 显示空状态 "暂无会话，点击上方按钮创建一个新的会话吧！"

### Requirement: 原型功能差异 — 原型缺失的现有功能
以下现有功能在设计原型中未体现，实现时 MUST 保留：
- 角色 badge 显示（"用户" / "技术支持"）
- 统计卡片使用真实后端数据（conversations 列表统计），非 mock 数据
- "创建会话" 使用 POST 表单 + CSRF（非 GET 链接到 chat page）
- 会话状态过滤使用 Jinja2 模板语法（`selectattr('status', 'equalto', ...)`）

### Requirement: 原型功能差异 — 原型有但当前不存在
以下原型功能当前不存在，暂不保留：
- "Resolved This Month"、"Avg. Response Time"、"Satisfaction Score" 统计 — 后端无对应数据
- "New Ticket" 直接跳转链接 — 保持 POST 表单创建会话
- Activity Feed（Recent Activity）— 后端无活动日志数据
- Recent Tickets 表格 — 当前使用列表视图，保持一致性
