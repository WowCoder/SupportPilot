## Why

当前页面 UI 使用旧的自定义样式，各页面风格不一致，缺乏统一的设计系统。需要基于新的 Apple-style 设计原型（`设计原型/整体页面重新设计-2026_5_26/`）对整个前端进行全面重构，建立统一、专业的企业级视觉体系。

## What Changes

- 将所有页面的 CSS 替换为新的统一设计系统 `style.css`（Apple-style, CSS 变量驱动）
- 将导航从旧 `navbar` 重构为新的 `topnav`（sticky + 毛玻璃 backdrop-filter）
- Login/Register 页面改为居中 `auth-page` 布局 + `auth-card` 卡片
- User Dashboard 改为 `stats-grid` 统计卡片 + `two-col` 布局（tickets table + activity feed）
- Tech Dashboard 改为 `stats-grid` + `filter-tabs` + `data-table` ticket queue + activity feed
- Conversation/Chat 页面改为 `chat-layout`（左侧会话列表 + 右侧消息区域 + ticket-bar + chat-composer）
- Document Upload 页面改为 `upload-shell` + `upload-zone` 拖拽区 + file-list + settings-panel toggles
- FAQ Management 页面改为 `filter-bar` + `filter-tabs` + `bulk-bar` + `faq-list` accordion + `modal`
- 新增 UI 组件：badge, status-dot, toast, toggle, modal, progress-bar
- 移除旧 CSS 中不再使用的样式规则
- 保留现有 Flask/Jinja2 模板语法和动态数据绑定逻辑

## Capabilities

### New Capabilities
- `design-system`: 统一设计系统 CSS（CSS 变量、组件样式、响应式、Apple-style）
- `auth-pages`: Login 和 Register 页面的 auth-page 布局重构
- `user-dashboard`: 用户仪表盘页面（stats-grid + two-col 布局）
- `tech-dashboard`: 技术支持仪表盘页面（stats-grid + filter-tabs + data-table）
- `chat-layout`: 会话/聊天页面（chat-layout 双栏布局 + ticket-bar + chat-composer）
- `upload-page`: 文档上传页面（upload-shell + upload-zone + settings-panel）
- `faq-manage-page`: FAQ 管理页面（filter-bar + accordion list + bulk-bar + modal）
- `base-layout`: 基础页面框架（topnav 导航 + page-content 布局 + flash messages）

### Modified Capabilities
<!-- 无现有 specs 需要修改 -->

## Impact

- **模板文件**: `templates/*.html`（全部 8 个模板文件需要重写）
- **静态资源**: `static/css/style.css`（完全替换为新设计系统）
- **路由**: 无变更（所有 `url_for` 端点保持不变）
- **后端 API**: 无变更
- **JS 交互** 需要在模板中内联实现（filter-tabs 切换、faq accordion、bulk 选择、toast 提示、drag-and-drop 等）
