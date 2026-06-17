## ADDED Requirements

### Requirement: Tech Dashboard 页面布局
技术支持仪表盘 SHALL 使用 topnav + page-content 布局，包含 section-header（标题 + 快捷操作按钮）、stats-grid（4 个统计卡片）、需关注会话区、全部会话列表。

#### Scenario: 页面结构
- **WHEN** 技术支持人员访问 Dashboard
- **THEN** 页面 MUST 显示 "技术支持仪表盘" 标题
- **THEN** 页面 MUST 显示 "上传文档" 和 "FAQ 管理" 快捷按钮

### Requirement: 统计卡片
Tech Dashboard SHALL 显示 4 个统计卡片：总会话数、进行中（active）、需关注（needs_attention）、已关闭（closed），每种使用不同颜色强调。

#### Scenario: 统计卡片颜色
- **WHEN** Tech Dashboard 页面加载
- **THEN** "总会话数" MUST 显示默认样式
- **THEN** "进行中" MUST 显示绿色（success）强调
- **THEN** "需关注" MUST 显示红色（danger）强调
- **THEN** "已关闭" MUST 显示琥珀色（warning）强调

### Requirement: 需关注会话列表
当存在 needs_attention 状态的会话时 SHALL 在独立卡片中高亮显示，每条包含红色 "需关注" badge 和创建时间。

#### Scenario: 需关注会话展示
- **WHEN** 存在 needs_attention 会话
- **THEN** MUST 显示独立卡片，标题含红色感叹号图标 "需关注的会话"
- **THEN** 每条会话 MUST 显示 "#会话ID" + 红色 badge "+ 需关注" + 创建时间

#### Scenario: 无需关注会话
- **WHEN** 没有 needs_attention 会话
- **THEN** 该卡片区域 MUST 不显示

### Requirement: 全部会话列表
Dashboard SHALL 显示所有会话列表，每条显示会话 ID、状态 badge（active=绿色/needs_attention=红色/closed=灰色）、创建时间、用户 ID，点击进入会话详情。

#### Scenario: 会话状态 badge
- **WHEN** 会话列表渲染
- **THEN** active 状态 MUST 显示绿色 badge "进行中"
- **THEN** needs_attention 状态 MUST 显示红色 badge "需关注"
- **THEN** closed 状态 MUST 显示灰色 badge "已关闭"

#### Scenario: 空会话列表
- **WHEN** 没有会话
- **THEN** MUST 显示空状态 "暂无会话"

### Requirement: 原型功能差异 — 原型缺失的现有功能
以下现有功能在设计原型中未体现，实现时 MUST 保留：
- "上传文档" 和 "FAQ 管理" 快捷操作按钮（技术支持核心入口）
- 统计卡片使用真实后端数据（conversations 列表 + Jinja2 `selectattr` 过滤）
- 需关注会话独立高亮区域
- 会话列表使用 Jinja2 模板渲染（非 JS 动态加载）
- 用户 ID 显示在每条会话中

### Requirement: 原型功能差异 — 原型有但当前不存在
以下原型功能当前不存在，暂不保留：
- "View Queue" / "Take Next Ticket" 按钮 — 当前无工单队列概念
- Ticket Queue 表格的 filter-tabs（All/Unassigned/Mine/Escalated）— 当前无分配系统
- Priority 列（Critical/High/Normal/Low）— 当前工单模型无优先级字段
- Team Activity Feed — 后端无活动日志
- "Assigned to You"、"Avg. First Reply" 等统计 — 后端无此数据
