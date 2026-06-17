## ADDED Requirements

### Requirement: Chat 页面双栏布局
会话页面 SHALL 使用 `.chat-layout` 双栏布局：左侧 `.chat-sidebar`（320px 会话列表）+ 右侧 `.chat-main`（消息区域 + 操作区 + composer）。

#### Scenario: 布局结构
- **WHEN** 用户打开某个会话页面
- **THEN** 左侧 MUST 显示会话列表 sidebar（宽度 320px）
- **THEN** 右侧 MUST 显示消息区域（flex: 1）

### Requirement: 会话页面头部
Chat main 顶部 SHALL 显示页面头部，包含会话 ID 标题、返回按钮、以及根据会话状态和用户角色的操作按钮。

#### Scenario: 技术支持操作按钮 — active 状态
- **WHEN** 技术支持人员查看 active 状态的会话
- **THEN** MUST 显示 "标记需关注" 按钮（warning 样式）
- **THEN** MUST 显示 "关闭会话" 按钮（danger 样式）

#### Scenario: 技术支持操作按钮 — needs_attention 状态
- **WHEN** 技术支持人员查看 needs_attention 状态的会话
- **THEN** MUST 显示 "解决并关闭" 按钮（success 样式）

#### Scenario: 技术支持操作按钮 — closed 状态
- **WHEN** 技术支持人员查看 closed 状态的会话
- **THEN** MUST 显示 "重新打开" 按钮（primary 样式）

### Requirement: 会话状态横幅
当会话状态为 needs_attention 或 closed 时，SHALL 在消息区域顶部显示对应的状态横幅。

#### Scenario: Needs attention 横幅
- **WHEN** 会话状态为 needs_attention
- **THEN** MUST 显示 warning 横幅："此会话需要技术支持关注！技术支持团队将尽快为您处理"

#### Scenario: Closed 横幅
- **WHEN** 会话状态为 closed
- **THEN** MUST 显示 info 横幅："此会话已关闭"

### Requirement: 用户工单状态栏（普通用户侧）
普通用户查看会话时，SHALL 在消息区域顶部显示工单状态栏，包含：状态 badge（进行中/待人工处理/已关闭）、轮次计数、人工介入按钮（第 3 轮后显示）、关闭工单按钮。

#### Scenario: 工单状态栏展示
- **WHEN** 普通用户打开一个 active 会话
- **THEN** MUST 显示状态 badge 和当前轮次
- **THEN** 轮次 >= 3 时 MUST 显示 "人工介入" 按钮

#### Scenario: 请求人工介入
- **WHEN** 用户点击 "人工介入" 按钮并确认
- **THEN** MUST 调用 `/api/ticket/<id>/handoff`（POST）
- **THEN** 成功后状态 badge MUST 变为 "待人工处理"
- **THEN** "人工介入" 按钮 MUST 隐藏

#### Scenario: 用户关闭工单
- **WHEN** 用户点击 "关闭" 按钮
- **THEN** MUST 打开关闭确认 modal
- **THEN** 确认后 MUST 调用 `/api/ticket/<id>/close`（POST）

### Requirement: 消息气泡
消息 MUST 按 sender_type 区分样式：user（右对齐，蓝色背景）、ai（左对齐，灰色背景，AI 助手标签）、tech_support（左对齐，灰色背景，技术支持标签），每条消息含发送者头像（U/AI/T）、名称、时间戳。

#### Scenario: User 消息渲染
- **WHEN** sender_type 为 "user"
- **THEN** 消息 MUST 右对齐，显示 "您" 标签、当前时间

#### Scenario: AI 消息渲染
- **WHEN** sender_type 为 "ai"
- **THEN** 消息 MUST 左对齐，显示 "AI 助手" 标签（sparkles 图标）

#### Scenario: 技术支持消息渲染
- **WHEN** sender_type 为 "tech_support"
- **THEN** 消息 MUST 左对齐，显示 "技术支持" 标签（headset 图标）

### Requirement: 消息输入区
会话未关闭时 SHALL 在底部显示消息输入区（chat-composer），含 textarea（支持 Enter 发送）、发送按钮。会话关闭时 MUST 显示 "会话已关闭" 提示。

#### Scenario: 发送消息
- **WHEN** 用户在 active 会话中输入文字并提交
- **THEN** MUST 通过 POST 表单提交到 `/conversation/<id>/send_message`
- **THEN** 页面 MUST 刷新显示新消息

#### Scenario: 会话已关闭
- **WHEN** 会话状态为 closed
- **THEN** composer MUST 不显示
- **THEN** MUST 显示 info 提示 "会话已关闭，如需继续咨询，请重新打开会话或创建新会话"

### Requirement: 滚动控制
消息列表 SHALL 在加载时自动滚动到底部，当用户向上滚动超过 100px 时显示浮动 "回到底部" 按钮，点击后平滑滚动。

#### Scenario: 自动滚到底部
- **WHEN** 页面加载完成
- **THEN** 消息列表 MUST 滚动到最底部

#### Scenario: 滚动按钮显示/隐藏
- **WHEN** 用户向上滚动超过 100px
- **THEN** 浮动 "回到底部" 按钮 MUST 显示
- **WHEN** 用户滚动回底部
- **THEN** 浮动按钮 MUST 隐藏

### Requirement: 关闭会话 Modal（技术支持）
技术支持关闭会话时 SHALL 弹出 modal，包含关闭确认文字和 "生成 FAQ" checkbox 选项（默认不勾选）。

#### Scenario: 关闭会话 Modal
- **WHEN** 技术支持点击 "关闭会话" 或 "解决并关闭"
- **THEN** MUST 弹出 modal 显示 "确认要关闭此会话吗？"
- **THEN** MUST 显示 checkbox："生成 FAQ — 从对话中提取 Q&A 对并录入知识库"
- **THEN** 确认后 MUST POST 到 `/conversation/<id>/close_conversation` 并携带 `generate_faq` 参数

### Requirement: 关闭工单 Modal（普通用户）
普通用户关闭工单时 SHALL 弹出 modal，包含确认文字和确认关闭按钮。

#### Scenario: 关闭工单 Modal
- **WHEN** 普通用户点击 "关闭" 按钮
- **THEN** MUST 弹出 modal 显示确认信息
- **THEN** 确认后 MUST 调用 `/api/ticket/<id>/close`（POST）

### Requirement: 原型功能差异 — 原型缺失的现有功能
以下现有功能在设计原型中未体现，实现时 MUST 保留：
- 页面头部操作按钮（标记需关注/关闭/解决并关闭/重新打开）根据角色和状态动态显示
- 状态横幅（needs_attention warning / closed info）
- 用户工单状态栏（状态 badge + 轮次 + 人工介入 + 关闭工单）
- 3 种消息发送者类型（user/AI/tech_support）而非原型的 2 种
- 浮动 "回到底部" 滚动按钮
- 关闭会话 Modal + FAQ 生成 checkbox
- 关闭工单 Modal（普通用户）
- 会话关闭后禁用输入区

### Requirement: 原型功能差异 — 原型有但当前不存在
以下原型功能当前不存在，暂不保留：
- 附件上传按钮（chat-composer 中的 paperclip 按钮）— 后端无附件 API
- Ticket info bar 中的 Priority/Assignee/Opened 字段 — 后端工单模型不同
- 多会话切换侧边栏 — 当前为单会话页面，非列表视图
