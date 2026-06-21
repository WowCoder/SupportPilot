## Context

SupportPilot 当前是 Flask + Jinja2 SSR 应用，服务端渲染全部页面。前端逻辑散落在 Jinja2 模板、`static/css/style.css` 和内联 `<script>` 中，依赖 jQuery 处理交互。API 蓝图已存在但返回格式不统一（部分返回 HTML 片段，部分返回 JSON），认证基于 Flask-Login Session + CSRF Token。

迁移目标是 **渐进式** 前后端分离：先用 Vue 3 重建前端，后端逐步 API 化，最终移除 SSR。整个迁移期间，新旧两套前端共存（通过 URL 前缀区分），不中断现有功能。

## Goals / Non-Goals

**Goals:**
- 新建 `frontend/` Vue 3 项目，使用 Vite + Element Plus + Pinia + Vue Router
- 后端统一 RESTful API 规范（`/api/v1/` 前缀、标准 JSON 响应格式、JWT 认证）
- 渐进式迁移，4 个 Phase 各自可独立上线验证
- 开发环境 Vite HMR + proxy 转发 API，生产环境 Nginx 静态托管 + 反向代理

**Non-Goals:**
- NOT 替换 Python 后端（Flask 保留，仅改为 API 服务）
- NOT 引入 TypeScript（初期用 JS + Composition API，后续可按需加 TS）
- NOT 引入 SSR/SSG（纯 SPA 模式）
- NOT 改动 RAG 引擎、LLM 客户端、数据库模型（除认证相关外）
- NOT 一次性全量迁移（Phase 1-3 旧模板并行存在）

## Decisions

### 1. 前端技术栈：Vue 3 + Vite + Element Plus + Pinia + Vue Router

**选型理由：**
- Vue 3 Composition API + `<script setup>` 学习曲线低，国内生态成熟
- Element Plus 提供完整的 Admin/客服场景组件（表格、表单、弹窗、消息流）
- Vite 开发体验极好（HMR < 1s），构建快
- Pinia 是 Vue 官方推荐的状态管理，API 简洁
- Vue Router 4 支持 Hash 和 History 模式，History 模式需要 Nginx 配合（生产环境配置 `try_files`）

**替代方案：**
- React + Ant Design → 国内也流行，但学习成本更高，团队如果不熟悉则风险大
- Nuxt 3 → 支持 SSR/SSG，但本项目后端已有 Flask API，SSR 无意义
- Svelte → 生态太小，组件库有限

### 2. 认证方案：JWT (Access + Refresh Token)

**架构：**
- 登录后返回 `access_token`（15min 过期）和 `refresh_token`（7 天过期）
- `access_token` 存前端内存（Pinia store），`refresh_token` 存 localStorage
- Axios 拦截器：401 时自动用 `refresh_token` 换新 `access_token`，换失败则跳转登录
- 后端：JWT 验证作为 Flask decorator 替代 `@login_required`
- 用户名/密码验证逻辑复用现有 `User` model（`check_password`），不修改数据库 schema

**为什么不继续用 Session？**
- Session Cookie 依赖同域，前后端分离后不同端口/域名下跨域 Cookie 配置复杂
- JWT 天然适合 API 鉴权，前端存储灵活
- 现有的 CSRF 保护在纯 API 场景下不适用（SPA 发的是 JSON，不存在 CSRF 问题）

**替代方案：**
- HttpOnly Cookie + SameSite → 安全但跨域配置复杂，不适合分离部署
- OAuth2/SAML → 太重，本项目不需要

### 3. API 层设计

**URL 规范：**
```
/api/v1/auth/login      POST   登录
/api/v1/auth/register   POST   注册
/api/v1/auth/refresh    POST   刷新 Token
/api/v1/chat/sessions   GET    会话列表
/api/v1/chat/sessions   POST   创建会话
/api/v1/chat/sessions/:id/messages  GET  消息列表
/api/v1/chat/sessions/:id/messages  POST 发送消息（支持 SSE 流式）
/api/v1/faq/entries     GET     FAQ 列表
/api/v1/faq/entries     POST    创建 FAQ
/api/v1/faq/entries/:id PUT     更新 FAQ
/api/v1/faq/entries/:id DELETE  删除 FAQ
/api/v1/documents       GET/POST  文档列表/上传
/api/v1/rag/dashboard   GET     RAG 仪表盘数据
/api/v1/rag/logs        GET     RAG 检索日志
```

**统一响应格式：**
```json
// 成功
{ "code": 200, "data": {...}, "message": "ok" }
// 失败
{ "code": 400, "data": null, "message": "Invalid username or password" }
// 分页
{ "code": 200, "data": { "items": [...], "total": 100, "page": 1, "page_size": 20 } }
```

**SSE 流式响应**（对话消息）沿用现有格式，不做变更。

### 4. 前端项目结构

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── .env.development       # VITE_API_BASE=http://localhost:5050
├── .env.production         # VITE_API_BASE=/api/v1
├── public/
│   └── favicon.svg
└── src/
    ├── main.js             # 入口：创建 app, use router/pinia/element-plus
    ├── App.vue             # 根组件：router-view + 全局 Layout
    ├── api/
    │   ├── index.js        # Axios 实例 + 拦截器（JWT, 错误处理）
    │   ├── auth.js         # 登录/注册/刷新 API
    │   ├── chat.js         # 会话/消息 API（含 SSE）
    │   ├── faq.js          # FAQ CRUD API
    │   ├── document.js     # 文档上传 API
    │   └── rag.js          # RAG 仪表盘 API
    ├── router/
    │   └── index.js        # 路由配置 + 导航守卫
    ├── stores/
    │   ├── auth.js         # 用户信息 + Token
    │   └── chat.js         # 当前会话状态
    ├── views/
    │   ├── Login.vue
    │   ├── Register.vue
    │   ├── ChatLayout.vue  # 双栏布局（sidebar + main）
    │   ├── FaqManage.vue
    │   ├── DocumentUpload.vue
    │   ├── RagDashboard.vue
    │   ├── TechDashboard.vue
    │   └── UserDashboard.vue
    ├── components/
    │   ├── layout/
    │   │   ├── AppTopnav.vue
    │   │   └── AppSidebar.vue
    │   ├── chat/
    │   │   ├── MessageBubble.vue
    │   │   ├── ChatInput.vue
    │   │   └── SessionList.vue
    │   └── common/
    │       ├── MarkdownRenderer.vue
    │       └── LoadingSpinner.vue
    ├── composables/        # 组合式函数
    │   ├── useSSE.js       # SSE 流式消息处理
    │   └── useAuth.js      # 认证逻辑封装
    └── utils/
        └── constants.js
```

### 5. 渐进式迁移策略

**Phase 1-3：新旧共存**
- Vue Router 使用 Hash 模式（`/#/login`），避免与 Flask 路由冲突
- 开发时通过 `VITE_API_BASE` 环境变量指向 Flask API 端口
- 旧 Jinja2 页面保持可访问，逐步被 Vue 页面替换

**Phase 4：完全切换**
- Vue Router 切换为 History 模式（`/login`）
- 删除 `templates/` 目录
- Nginx 配置 `try_files $uri /index.html` 实现 SPA fallback

### 6. 部署架构

**开发环境：**
```
Browser → localhost:5173 (Vite dev server)
              ├── Serves Vue SPA
              └── /api/v1/* → proxy to localhost:5050 (Flask)
```

**生产环境：**
```
Browser → Nginx :80
              ├── /assets/* → static files (frontend/dist/assets/)
              ├── /api/v1/* → proxy to Flask :5050
              └── /* → frontend/dist/index.html (SPA fallback)
```

## Risks / Trade-offs

- **[SEO 不友好]** → SPA 默认对搜索引擎不友好。但 SupportPilot 是内部客服系统（需登录），SEO 无意义，风险可接受。
- **[首屏加载慢]** → Vite Tree Shaking + 路由懒加载 + CDN 可缓解。Element Plus 支持按需导入减少 bundle 体积。
- **[迁移期代码冗余]** → Phase 1-3 期间两套前端共存，维护成本略增。限定迁移窗口期（4 周内完成），到 Phase 4 统一清理。
- **[JWT 安全性]** → access_token 存在 JS 内存中有 XSS 风险。缓解：CSP 头 + 输入输出转义 + access_token 短有效期（15min）。
- **[SSE 兼容]** → 现有 SSE 流式消息依赖 `text/event-stream`，Axios 原生不支持 SSE 流式读取。用 `EventSource` API 或 `fetch` + `ReadableStream` 处理，需要传 Token 时用 `EventSource` polyfill 或改 URL query 参数传 Token。

## Open Questions

- 现有移动端或其他系统是否直接调 Flask API？如果是，API 格式变更需协调。
- refresh_token 存储策略：localStorage vs sessionStorage？（建议 localStorage，因为用户期望"记住我"）
- Element Plus 主题：沿用现有蓝色配色还是重新设计？（建议保留现有设计 token 映射到 Element Plus CSS 变量）
