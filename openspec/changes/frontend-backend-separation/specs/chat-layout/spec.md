## MODIFIED Requirements

### Requirement: Chat 页面双栏布局
会话页面 SHALL 使用 Vue 组件实现双栏布局：左侧会话列表 sidebar（320px）+ 右侧消息区域（flex: 1）。

#### Scenario: 布局结构
- **WHEN** 用户通过 Vue Router 进入 Chat 页面
- **THEN** 左侧 MUST 显示 `<SessionList>` 组件（宽度 320px）
- **THEN** 右侧 MUST 显示消息区域（`<ChatMain>` 组件，flex: 1）
- **THEN** MUST 使用 Element Plus `el-container`/`el-aside`/`el-main` 或 CSS Grid/Flex 实现

### Requirement: 会话页面头部
Chat main 顶部 SHALL 显示页面头部组件，包含会话标题、返回按钮、以及根据会话状态和用户角色的操作按钮（使用 Element Plus `el-button`）。

#### Scenario: 技术支持操作按钮 — active 状态
- **WHEN** 技术支持人员查看 active 状态的会话
- **THEN** MUST 显示 `el-button type="warning"` "标记需关注"
- **THEN** MUST 显示 `el-button type="danger"` "关闭会话"

#### Scenario: 技术支持操作按钮 — needs_attention 状态
- **WHEN** 技术支持人员查看 needs_attention 状态的会话
- **THEN** MUST 显示 `el-button type="success"` "解决并关闭"

#### Scenario: 技术支持操作按钮 — closed 状态
- **WHEN** 技术支持人员查看 closed 状态的会话
- **THEN** MUST 显示 `el-button type="primary"` "重新打开"

### Requirement: 会话状态横幅
当会话状态为 needs_attention 或 closed 时，SHALL 在消息区域顶部使用 `el-alert` 显示对应的状态横幅。

#### Scenario: Needs attention 横幅
- **WHEN** 会话状态为 needs_attention
- **THEN** MUST 显示 `el-alert type="warning"` "此会话需要技术支持关注！"

#### Scenario: Closed 横幅
- **WHEN** 会话状态为 closed
- **THEN** MUST 显示 `el-alert type="info"` "此会话已关闭"

### Requirement: 用户工单状态栏（普通用户侧）
普通用户查看会话时，SHALL 在消息区域顶部显示工单状态栏，使用 Element Plus `el-tag` 显示状态、轮次计数、操作按钮。

#### Scenario: 工单状态栏
- **WHEN** 普通用户打开一个 active 会话
- **THEN** MUST 显示状态 `el-tag` 和当前轮次
- **THEN** 轮次 >= 3 时 MUST 显示 "人工介入" 按钮
- **THEN** 操作 MUST 通过 Axios 调用 API（非 POST 表单）

### Requirement: 消息气泡
消息 MUST 使用 Vue 组件 `<MessageBubble>` 渲染，根据 `sender_type` prop 区分样式：user（右对齐蓝色）、ai（左对齐灰色+AI 标签）、tech_support（左对齐灰色+技术支持标签）。

#### Scenario: User 消息渲染
- **WHEN** `sender_type === "user"`
- **THEN** 消息 MUST 右对齐，蓝色背景，显示 "您" 标签

#### Scenario: AI 消息渲染
- **WHEN** `sender_type === "ai"`
- **THEN** 消息 MUST 左对齐，灰色背景，显示 `el-icon` sparkles + "AI 助手" 标签
- **THEN** 内容 MUST 支持 Markdown 渲染

#### Scenario: 技术支持消息渲染
- **WHEN** `sender_type === "tech_support"`
- **THEN** 消息 MUST 左对齐，灰色背景，显示 `el-icon` headset + "技术支持" 标签

### Requirement: 消息输入区
会话未关闭时 SHALL 在底部显示 `<ChatInput>` 组件（Element Plus `el-input` textarea + 发送按钮），支持 Enter 发送。会话关闭时 MUST 显示 "会话已关闭" 提示。

#### Scenario: 发送消息
- **WHEN** 用户在 active 会话中输入文字并按下 Enter（或点击发送按钮）
- **THEN** MUST 通过 Axios POST JSON 发送消息
- **THEN** MUST NOT 使用表单 POST 触发页面刷新

#### Scenario: 会话已关闭
- **WHEN** 会话状态为 closed
- **THEN** ChatInput MUST 不可用（`disabled`）
- **THEN** MUST 显示 `el-alert type="info"` 提示

### Requirement: 滚动控制
消息列表 SHALL 使用 `el-scrollbar` 或自定义滚动容器，加载时自动滚动到底部，向上滚动超过 100px 时显示浮动 "回到底部" 按钮，使用 `el-backtop`。

#### Scenario: 自动滚到底部
- **WHEN** 消息列表更新（新消息到达）
- **THEN** 滚动容器 MUST `scrollTo` 底部（`nextTick` 内执行）

#### Scenario: 回到底部按钮
- **WHEN** 用户向上滚动超过 100px
- **THEN** `el-backtop` 或自定义浮动按钮 MUST 显示
- **THEN** 点击后 MUST 平滑滚动到底部

### Requirement: 关闭会话 Modal（技术支持）
技术支持关闭会话时 SHALL 弹出 `el-dialog` Modal，包含关闭确认文字和 `el-checkbox` "生成 FAQ" 选项。

#### Scenario: 关闭会话 Modal
- **WHEN** 技术支持点击 "关闭会话" 或 "解决并关闭"
- **THEN** `el-dialog` MUST 弹出
- **THEN** MUST 显示 `el-checkbox`："生成 FAQ — 从对话中提取 Q&A 对并录入知识库"
- **THEN** 确认后 MUST Axios POST 并携带 `generate_faq` 参数

### Requirement: 关闭工单 Modal（普通用户）
普通用户关闭工单时 SHALL 弹出 `el-message-box.confirm` 确认对话框。

#### Scenario: 关闭工单
- **WHEN** 普通用户点击 "关闭" 按钮
- **THEN** `el-message-box.confirm` MUST 弹出确认信息
- **THEN** 确认后 MUST Axios POST 调用关闭 API

## REMOVED Requirements

### Requirement: 原型功能差异 — 原型缺失的现有功能
**Reason**: 前端完全重写，所有交互改为 Vue 响应式 + Element Plus 组件实现
**Migration**: Jinja2 模板和 jQuery 交互全部替换为 Vue 组件；CSS class 映射到 Element Plus 组件

### Requirement: 原型功能差异 — 原型有但当前不存在
**Reason**: Vue 重写以现有功能为基准
**Migration**: 附件上传等功能在后续版本通过 Element Plus Upload 组件实现
