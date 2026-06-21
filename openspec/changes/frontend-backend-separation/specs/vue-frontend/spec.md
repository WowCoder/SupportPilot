## ADDED Requirements

### Requirement: Vue 3 项目初始化
前端项目 SHALL 使用 `npm create vue@latest` 创建，基于 Vite 构建，目录名为 `frontend/`，位于项目根目录。

#### Scenario: 项目结构
- **WHEN** 创建 Vue 3 项目
- **THEN** MUST 生成 `frontend/package.json` 包含 vue 3.x、vue-router 4.x、pinia、element-plus 依赖
- **THEN** MUST 生成 `frontend/vite.config.js` 包含基础 Vite 配置
- **THEN** MUST 生成 `frontend/index.html` 作为 SPA 入口
- **THEN** MUST 生成 `frontend/src/main.js` 作为 JS 入口

### Requirement: 依赖管理
前端项目 SHALL 包含以下核心依赖：`vue@^3.4`、`vue-router@^4`、`pinia@^2`、`element-plus@^2`、`axios@^1`。

#### Scenario: 核心依赖安装
- **WHEN** `npm install` 在 `frontend/` 目录执行
- **THEN** MUST 安装 vue、vue-router、pinia、element-plus、axios
- **THEN** `package.json` MUST 记录精确版本号

### Requirement: Vite 开发服务器代理
Vite 开发服务器 SHALL 将 `/api/v1` 前缀的请求代理转发到 Flask 后端（默认 `http://localhost:5050`）。

#### Scenario: API 代理配置
- **WHEN** 前端发起 `GET /api/v1/faq/entries`
- **THEN** Vite MUST 将请求代理到 `http://localhost:5050/api/v1/faq/entries`
- **THEN** 浏览器不遇到跨域错误

### Requirement: 环境变量管理
前端项目 SHALL 使用 `.env.development` 和 `.env.production` 管理环境变量，`VITE_API_BASE` 指定 API 基础路径。

#### Scenario: 开发环境
- **WHEN** `npm run dev` 启动
- **THEN** `VITE_API_BASE` MUST 设为空字符串（走 Vite proxy）
- **THEN** API 请求路径为 `/api/v1/...`

#### Scenario: 生产环境
- **WHEN** `npm run build` 构建
- **THEN** `VITE_API_BASE` MUST 设为 `/api/v1`
- **THEN** 构建产物中的 API 请求路径为 `/api/v1/...`

### Requirement: Element Plus 集成
Element Plus 组件库 SHALL 全局注册，支持按需导入以减少 bundle 体积。

#### Scenario: 全局注册
- **WHEN** Vue 应用启动
- **THEN** Element Plus 组件、指令、样式 MUST 全局可用
- **THEN** 中文语言包 MUST 配置为默认

### Requirement: Pinia 状态管理
Pinia SHALL 作为全局状态管理方案，创建 `auth` store（用户信息 + Token）和 `chat` store（当前会话状态）。

#### Scenario: Auth Store
- **WHEN** 用户登录成功
- **THEN** auth store MUST 存储 access_token、用户信息（username、role、email）
- **THEN** 页面刷新后 store 可从 localStorage 恢复 refresh_token

#### Scenario: Chat Store
- **WHEN** 用户进入对话页面
- **THEN** chat store MUST 管理当前会话 ID、消息列表、未读状态

### Requirement: Vue Router 配置
Vue Router SHALL 配置所有页面路由，初始阶段使用 Hash 模式避免与 Flask 路由冲突，包含导航守卫检查认证状态。

#### Scenario: 路由表
- **WHEN** Vue Router 初始化
- **THEN** MUST 包含路由：`/login`、`/register`、`/chat`、`/chat/:id`、`/faq`、`/upload`、`/rag-dashboard`、`/tech-dashboard`、`/user-dashboard`

#### Scenario: 认证守卫
- **WHEN** 未登录用户访问 `/chat`
- **THEN** 导航守卫 MUST 重定向到 `/login`
- **WHEN** 已登录用户访问 `/login`
- **THEN** 导航守卫 MUST 重定向到默认首页

#### Scenario: 权限守卫
- **WHEN** 普通用户访问 `/rag-dashboard`
- **THEN** 导航守卫 MUST 重定向到首页并提示权限不足
