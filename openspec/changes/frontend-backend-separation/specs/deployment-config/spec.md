## ADDED Requirements

### Requirement: 开发环境 Vite Proxy
Vite 开发服务器 SHALL 配置 proxy，将 `/api/v1` 请求转发到 Flask 后端，避免跨域问题。

#### Scenario: Proxy 配置
- **WHEN** `npm run dev` 启动 Vite
- **THEN** `vite.config.js` proxy 配置 MUST 将 `/api/v1` 请求转发到 `http://localhost:5050`
- **THEN** 浏览器发起的 `/api/v1/*` 请求不产生跨域错误

### Requirement: 生产环境 Nginx 配置
生产环境 SHALL 通过 Nginx 提供静态文件和 API 反向代理。

#### Scenario: Nginx SPA 路由
- **WHEN** 用户访问 `/login` 或 `/chat`（非 `/api` 非 `/assets` 路径）
- **THEN** Nginx MUST 返回 `frontend/dist/index.html`（SPA fallback）
- **THEN** Vue Router（History 模式）接管路由

#### Scenario: Nginx API 代理
- **WHEN** 请求路径为 `/api/v1/*`
- **THEN** Nginx MUST 代理到 Flask 后端（`http://127.0.0.1:5050`）

#### Scenario: Nginx 静态资源
- **WHEN** 请求路径为 `/assets/*`
- **THEN** Nginx MUST 直接从 `frontend/dist/assets/` 提供静态文件，设置 1 年缓存

### Requirement: Docker Compose 编排
项目根目录 SHALL 提供 `docker-compose.yml`，定义 `frontend`（Nginx + Vue 静态文件）和 `backend`（Flask + Gunicorn）两个服务。

#### Scenario: 容器化部署
- **WHEN** `docker-compose up` 执行
- **THEN** frontend 服务 MUST 在 80 端口提供 Nginx + Vue SPA
- **THEN** backend 服务 MUST 在 5050 端口提供 Flask API
- **THEN** frontend 通过内部网络 `proxy_pass` 到 backend

### Requirement: 前端构建配置
`npm run build` SHALL 使用 Vite 构建优化后的静态文件到 `frontend/dist/`，生产环境 `VITE_API_BASE` 设为 `/api/v1`。

#### Scenario: 生产构建
- **WHEN** `npm run build` 执行
- **THEN** MUST 输出压缩后的 JS/CSS 到 `frontend/dist/assets/`
- **THEN** index.html MUST 使用相对路径或正确的 base 路径
- **THEN** API 请求路径 MUST 为 `/api/v1/...`（不包含主机名）

### Requirement: 启动脚本更新
项目 `start.sh` SHALL 更新为同时启动前端 dev server 和后端 Flask 服务。

#### Scenario: 开发启动
- **WHEN** `bash start.sh` 执行
- **THEN** MUST 后台启动 Flask（端口 5050）
- **THEN** MUST 前台启动 Vite dev server（端口 5173）
- **THEN** 终端 MUST 显示两个服务的访问地址
