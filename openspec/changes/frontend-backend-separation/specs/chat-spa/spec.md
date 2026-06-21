## ADDED Requirements

### Requirement: Chat SPA 双栏布局
Chat SPA 页面 SHALL 使用 Element Plus `el-container` 实现双栏布局：左侧会话列表 sidebar（320px）+ 右侧消息区域（flex: 1）。

#### Scenario: 布局结构
- **WHEN** 用户进入 `/chat` 路由
- **THEN** 左侧 MUST 显示会话列表（SessionList 组件，宽度 320px）
- **THEN** 右侧 MUST 显示消息区域或空状态提示

#### Scenario: 响应式折叠
- **WHEN** 视口宽度 < 768px
- **THEN** 左侧 sidebar MUST 默认折叠，通过 hamburger 按钮展开

### Requirement: 会话列表
左侧 sidebar SHALL 显示用户的所有会话列表，每项包含会话标题、最后消息预览、时间戳、未读标记。支持创建新会话。

#### Scenario: 会话列表加载
- **WHEN** ChatLayout 组件 mounted
- **THEN** MUST 调用 `GET /api/v1/chat/sessions` 加载会话列表
- **THEN** 当前选中的会话 MUST 高亮

#### Scenario: 创建新会话
- **WHEN** 用户点击 "新建会话" 按钮
- **THEN** MUST 调用 `POST /api/v1/chat/sessions`
- **THEN** 新会话 MUST 出现在列表顶部并自动选中

#### Scenario: 切换会话
- **WHEN** 用户点击某个会话项
- **THEN** Vue Router MUST 切换到 `/chat/:id`（路由参数变化但不重新挂载 ChatLayout）

### Requirement: 消息流渲染
右侧消息区域 SHALL 使用 `v-for` 渲染消息列表，根据 `sender_type` 区分气泡样式：user（右对齐蓝色）、ai（左对齐灰色）、tech_support（左对齐灰色带标签）。

#### Scenario: User 消息渲染
- **WHEN** `sender_type === "user"`
- **THEN** 消息气泡 MUST 右对齐，蓝色背景（#1890ff），显示 "您" 标签

#### Scenario: AI 消息渲染
- **WHEN** `sender_type === "ai"`
- **THEN** 消息气泡 MUST 左对齐，灰色背景（#f5f5f5），显示 "AI 助手" 标签（sparkles 图标）
- **THEN** 内容 MUST 支持 Markdown 渲染（使用 marked 库或 Element Plus 文本组件）

#### Scenario: 技术支持消息渲染
- **WHEN** `sender_type === "tech_support"`
- **THEN** 消息气泡 MUST 左对齐，灰色背景，显示 "技术支持" 标签（headset 图标）

### Requirement: 流式消息展示
AI 回复 SHALL 通过 SSE（Server-Sent Events）流式接收并在页面实时渲染打字效果。

#### Scenario: SSE 流式接收
- **WHEN** 用户发送消息后
- **THEN** 前端 MUST 建立 SSE 连接到 `/api/v1/chat/sessions/:id/messages`（POST）
- **THEN** 新消息气泡 MUST 出现并随着数据到达逐字填充
- **THEN** 流结束时 MUST 标记消息为完成状态

### Requirement: 消息输入区
Chat SPA 底部 SHALL 显示消息输入区（Element Plus `el-input` textarea + 发送按钮），支持 Enter 发送。

#### Scenario: 发送消息
- **WHEN** 用户在 active 会话中输入文字并按下 Enter（或点击发送按钮）
- **THEN** MUST POST 消息到 `/api/v1/chat/sessions/:id/messages`
- **THEN** 输入区 MUST 清空
- **THEN** 消息列表 MUST 滚动到底部

#### Scenario: 会话已关闭
- **WHEN** 会话状态为 closed
- **THEN** 输入区 MUST 不可用并显示 "会话已关闭" 提示

### Requirement: 操作按钮
Chat 页面头部 SHALL 根据用户角色和会话状态动态显示操作按钮（标记需关注/关闭/解决并关闭/重新打开）。

#### Scenario: 技术支持操作（active 状态）
- **WHEN** 技术支持查看 active 会话
- **THEN** MUST 显示 "标记需关注" 和 "关闭会话" 按钮

#### Scenario: 普通用户操作
- **WHEN** 普通用户查看自己的会话
- **THEN** MUST 显示 "请求人工介入" 按钮（第 3 轮后）和 "关闭工单" 按钮

### Requirement: 自动滚动与"回到底部"
消息列表 SHALL 在收到新消息时自动滚动到底部；当用户向上滚动超过 100px 时显示浮动 "回到底部" 按钮。

#### Scenario: 自动滚到底部
- **WHEN** 新消息到达
- **THEN** 消息容器 MUST 自动 `scrollTo` 底部

#### Scenario: 滚动按钮显示
- **WHEN** 用户向上滚动超过 100px
- **THEN** Element Plus `el-backtop` 或自定义浮动按钮 MUST 显示

### Requirement: 关闭会话 Modal
技术支持关闭会话时 SHALL 弹出 Element Plus `el-dialog` Modal，包含关闭确认和 "生成 FAQ" checkbox 选项。

#### Scenario: 关闭 Modal
- **WHEN** 技术支持点击 "关闭会话"
- **THEN** `el-dialog` MUST 弹出显示确认信息
- **THEN** 包含 `el-checkbox`："生成 FAQ — 从对话中提取 Q&A 对并录入知识库"
- **THEN** 确认后 MUST POST 到后端并携带 `generate_faq` 参数
