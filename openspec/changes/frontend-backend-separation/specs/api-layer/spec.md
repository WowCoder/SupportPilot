## ADDED Requirements

### Requirement: API 版本化
所有新 API 端点 SHALL 使用 `/api/v1/` 前缀，与现有 `/api/` 端点共存直至 Phase 4 统一。

#### Scenario: 版本共存
- **WHEN** 前端请求 `/api/v1/faq/entries`
- **THEN** 后端 MUST 返回新格式 JSON 响应
- **WHEN** 旧页面请求 `/api/faq`
- **THEN** 后端 MUST 保持现有行为不变（Phase 1-3）

### Requirement: 统一 JSON 响应格式
所有 `/api/v1/` 端点 SHALL 返回统一格式：`{ "code": <http_status>, "data": <payload>, "message": "<description>" }`。

#### Scenario: 成功响应
- **WHEN** API 请求成功
- **THEN** 响应 MUST 包含 `code` 字段（200/201）、`data` 字段（payload 或 null）、`message` 字段

#### Scenario: 错误响应
- **WHEN** API 请求失败（客户端错误或服务端错误）
- **THEN** 响应 MUST 包含 `code` 字段（4xx/5xx）、`data` 字段（null）、`message` 字段（错误说明）

### Requirement: 分页响应格式
需要分页的 API 端点 SHALL 接受 `page`（默认 1）和 `page_size`（默认 20）query 参数，返回 `{ code, data: { items, total, page, page_size } }`。

#### Scenario: 分页请求
- **WHEN** 请求 `GET /api/v1/faq/entries?page=2&page_size=20`
- **THEN** 响应 `data` MUST 包含 `items`（当前页数据）、`total`（总数）、`page`（当前页码）、`page_size`（每页条数）

### Requirement: CORS 配置
后端 SHALL 通过 `flask-cors` 启用跨域支持，允许 Vue dev server（`http://localhost:5173`）在开发环境跨域请求。

#### Scenario: 开发环境 CORS
- **WHEN** `FLASK_ENV=development`
- **THEN** CORS MUST 允许 `http://localhost:5173` 来源
- **THEN** MUST 允许 `Authorization`、`Content-Type` 自定义头
- **THEN** MUST 允许 OPTIONS 预检请求

### Requirement: 现有 API 蓝图路径更新
现有 API 蓝图的 URL 前缀 SHALL 逐步迁移到 `/api/v1`，开发期间保留旧路由的兼容性。

#### Scenario: 蓝图注册
- **WHEN** Flask 应用启动
- **THEN** `app/api/chat.py` 的蓝图 SHALL 注册在 `/api/v1` 前缀
- **THEN** `app/api/faq.py` 的蓝图 SHALL 注册在 `/api/v1` 前缀
- **THEN** 旧 `/api` 蓝图保持可用（Phase 1-3）
