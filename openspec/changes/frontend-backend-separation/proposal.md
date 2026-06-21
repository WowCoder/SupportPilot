## Why

当前项目使用 Flask + Jinja2 服务端渲染，前端和后端耦合在同一进程中。开发体验差（无 HMR、无组件化、无类型提示），页面交互依赖 jQuery，难以实现现代客服系统需要的实时响应能力（消息流、Markdown 渲染、流式输出展示）。分离后前端可独立开发/部署/CDN 托管，后端纯 API 化更易扩展和测试。

## What Changes

- **新建 Vue 3 前端项目**：Vue 3 + Vite + Element Plus + Pinia + Vue Router，现代化组件式开发
- **后端 API 规范化**：现有 Flask 路由改造为 RESTful JSON API，统一 `/api/v1/` 前缀，JWT 认证替代 Flask Session + CSRF
- **渐进式迁移**：分 4 个阶段，每阶段可独立交付验证，不中断现有功能
  - Phase 1: 基础设施（Vue 项目搭建、API 层封装、登录/注册页迁移）
  - Phase 2: 核心页面（客服对话页、FAQ 管理页、文档上传页）
  - Phase 3: 后台管理（RAG 仪表盘、用户/技术仪表盘、配置管理）
  - Phase 4: 收尾（删除 Jinja2 模板和 CSRF 逻辑，纯 API 化）
- **部署方案**：开发环境 Vite dev server proxy 转发 Flask API；生产环境 Nginx 静态文件 + 反向代理
- **移除**：所有 Jinja2 模板文件、CSRF 相关逻辑、Flask Session 页面鉴权（改为 JWT API 鉴权）
- **BREAKING**: 前端 URL 路由切换至 Vue Router（Hash 或 History 模式），原 Flask 页面路由在 Phase 4 移除

## Capabilities

### New Capabilities

- `vue-frontend`: Vue 3 + Vite 前端项目搭建，包括项目结构、构建配置、开发代理、环境变量管理
- `api-authentication`: JWT 认证体系替代 Flask Session，包括登录/注册 API、Token 刷新、前端拦截器
- `api-layer`: 后端 API 层规范化，统一 `/api/v1/` 前缀，RESTful 设计，请求/响应格式标准化
- `chat-spa`: 客服对话 SPA 页面，包含会话列表、消息流、Markdown 渲染、流式输出、操作按钮
- `faq-management-spa`: FAQ 管理 SPA 页面，包含 CRUD、审核工作流、分类筛选
- `document-upload-spa`: 文档上传 SPA 页面，包含拖拽上传、进度显示、文档列表管理
- `rag-dashboard-spa`: RAG 仪表盘 SPA 页面，包含检索性能指标、日志查看、配置管理
- `deployment-config`: 部署配置，开发环境 Vite proxy + 生产环境 Nginx，Docker Compose 编排

### Modified Capabilities

（以下现有 specs 涉及页面路由/模板/CSRF，在新架构中需求变更）

- `auth-pages`: 从 Jinja2 SSR 页面 → Vue SPA 组件，移除 CSRF 依赖，改为 JWT Token 认证
- `chat-layout`: 从 Jinja2 + jQuery 页面 → Vue 组件化实现，消息流改为响应式数据驱动
- `rag-dashboard-page`: 从 Jinja2 SSR → Vue SPA，API 调用方式从表单提交改为 Axios + JWT
- `faq-manage-page`: 从 Jinja2 SSR → Vue SPA，表单交互改为 Element Plus 组件
- `upload-page`: 从 Jinja2 SSR → Vue SPA，上传逻辑改为 Axios + 进度事件

## Impact

- **新增目录**：`frontend/`（Vue 3 项目，约 50+ 文件），`config/nginx.conf`（生产 Nginx 配置）
- **修改文件**：
  - `app/__init__.py`：蓝图 CSRF 豁免扩大（最终移除 CSRF 依赖）
  - `app/api/`：所有路由文件增加 JSON 返回，统一错误格式
  - `app/models/user.py`：可能增加 JWT 相关字段
  - `requirements.txt`：新增 `PyJWT`、`flask-cors`
  - `wsgi.py`：可能增加 CORS 配置
- **删除文件**（Phase 4）：
  - `templates/`：全部 9 个 Jinja2 模板
  - `static/css/style.css`：前端样式迁移至 Vue 组件
  - CSRF 相关逻辑
- **新增依赖**（后端）：`PyJWT>=2.8`、`flask-cors>=4.0`
- **开发体验提升**：Vite HMR 热更新、TypeScript 类型检查（可选）、Vue DevTools 调试
