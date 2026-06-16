## ADDED Requirements

### Requirement: CSS 变量设计令牌
系统 SHALL 定义一组 CSS 自定义属性（设计令牌），包括颜色、字体、圆角、阴影、间距变量，所有组件样式 MUST 引用这些变量。

#### Scenario: 颜色变量可用
- **WHEN** 页面加载 `static/css/style.css`
- **THEN** 所有颜色变量（`--bg`, `--surface`, `--fg`, `--muted`, `--border`, `--accent`, `--danger`, `--success`, `--warning` 及其 light 变体）MUST 可用于任何 CSS 规则

#### Scenario: 字体栈正确
- **WHEN** 页面在任何操作系统渲染
- **THEN** 系统字体栈（`-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif`）MUST 生效，无需加载外部字体文件

### Requirement: 按钮组件
系统 SHALL 提供按钮组件（`.btn`），支持 primary, secondary, ghost, danger 四种变体和 sm/xs/icon 尺寸修饰符。

#### Scenario: 按钮变体渲染
- **WHEN** 页面包含 `<button class="btn btn-primary">`, `<button class="btn btn-secondary">`, `<button class="btn btn-ghost">`, `<button class="btn btn-danger">`
- **THEN** 每个按钮 MUST 以对应的背景色和文字颜色渲染
- **THEN** hover 时 MUST 有视觉反馈（颜色变化）

### Requirement: 表单组件
系统 SHALL 提供表单输入组件（`.form-input`, `.form-label`, `.form-group`），支持 text/email/password/textarea/select 类型，含 focus 和 error 状态。

#### Scenario: 输入框 focus 状态
- **WHEN** 用户聚焦一个 `.form-input`
- **THEN** 边框 MUST 变为 accent 颜色（`--accent`），并显示 3px 蓝色阴影

#### Scenario: 输入框 error 状态
- **WHEN** 一个 `.form-input` 带有 `.error` class
- **THEN** 边框 MUST 变为 danger 颜色（`--danger`）

### Requirement: 卡片组件
系统 SHALL 提供 `.card` 组件，包含 `.card-header` 和 `.card-title` 子元素，用于包裹内容区块。

#### Scenario: 卡片渲染
- **WHEN** 页面包含 `<div class="card"><div class="card-header"><span class="card-title">Title</span></div></div>`
- **THEN** 卡片 MUST 有白色背景、1px 边框、14px 圆角

### Requirement: 数据表格组件
系统 SHALL 提供 `.data-table` 组件，用 `.data-table-wrap` 包裹，表头大写字母、hover 行高亮。

#### Scenario: 表格 hover 效果
- **WHEN** 用户鼠标悬停在表格行上
- **THEN** 该行背景 MUST 变为半透明黑色（rgba(0,0,0,.015)）

### Requirement: Badge 状态标签
系统 SHALL 提供 `.badge` 组件，支持 blue/green/amber/red/gray 五种颜色变体。

#### Scenario: Badge 颜色变体
- **WHEN** 页面包含 `<span class="badge badge-red">Critical</span>`
- **THEN** badge MUST 以红色背景和深红色文字渲染

### Requirement: 统计卡片网格
系统 SHALL 提供 `.stats-grid` 和 `.stat-card` 组件，使用 CSS Grid 自动响应式排列，每个卡片包含图标、数值、标签。

#### Scenario: 响应式网格
- **WHEN** 视口宽度 > 768px
- **THEN** 统计卡片 MUST 至少在每行排列 2 列（`minmax(200px, 1fr)`）

### Requirement: Filter Tabs 分段控件
系统 SHALL 提供 `.filter-tabs` 和 `.filter-tab` 组件，用于分类筛选切换。

#### Scenario: Active tab 状态
- **WHEN** 一个 `.filter-tab` 带有 `.active` class
- **THEN** 该 tab MUST 有白色背景和阴影，区别于未选中 tab

### Requirement: Modal 弹窗
系统 SHALL 提供 `.modal-overlay` 和 `.modal` 组件，含毛玻璃 backdrop-filter 背景。

#### Scenario: Modal 显示
- **WHEN** `.modal-overlay` 的 `display` 不为 `none`
- **THEN** modal MUST 在视口居中显示，背景半透明 + 毛玻璃模糊

### Requirement: Toast 提示
系统 SHALL 提供 `.toast` 组件，固定在页面底部居中，含显示/隐藏过渡动画。

#### Scenario: Toast 显示
- **WHEN** `.toast` 元素添加 `.show` class
- **THEN** opacity MUST 从 0 过渡到 1，持续 0.25s

### Requirement: Toggle 开关
系统 SHALL 提供 `.toggle` 组件，iOS 风格开关，含轨道和滑块动画。

#### Scenario: Toggle 切换
- **WHEN** toggle 的 `<input type="checkbox">` 被选中
- **THEN** 轨道 MUST 变为 accent 蓝色，滑块 MUST 右移 20px

### Requirement: 响应式适配
系统 SHALL 在 768px 断点以下自动调整布局：隐藏 sidebar、全宽 chat-layout、2 列 stats-grid。

#### Scenario: 移动端 sidebar 隐藏
- **WHEN** 视口宽度 <= 768px
- **THEN** `.sidebar` MUST `display: none`

### Requirement: Reduce Motion 支持
系统 SHALL 在用户系统偏好为 `prefers-reduced-motion: reduce` 时禁用所有过渡和动画。

#### Scenario: 减少动画
- **WHEN** 用户操作系统设置为 reduced motion
- **THEN** 所有 `animation-duration` 和 `transition-duration` MUST 被设为 0.01ms
