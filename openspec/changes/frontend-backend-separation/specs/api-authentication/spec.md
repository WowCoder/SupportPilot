## ADDED Requirements

### Requirement: JWT Token 生成
后端 SHALL 提供 JWT access_token 和 refresh_token 生成能力，access_token 有效期 15 分钟，refresh_token 有效期 7 天。

#### Scenario: Token 生成
- **WHEN** 用户登录成功
- **THEN** MUST 返回 `{ "access_token": "<jwt>", "refresh_token": "<jwt>", "user": {...} }`
- **THEN** access_token payload MUST 包含 `sub`（user_id）、`role`、`exp`
- **THEN** refresh_token payload MUST 包含 `sub`（user_id）、`type: "refresh"`、`exp`

### Requirement: JWT 认证装饰器
后端 SHALL 提供 `@jwt_required` 装饰器替代 `@login_required`，从 `Authorization: Bearer <token>` 头提取并验证 Token。

#### Scenario: Token 验证成功
- **WHEN** 请求携带有效的 `Authorization: Bearer <token>` 头
- **THEN** `@jwt_required` 装饰器 MUST 注入 `current_user` 到请求上下文
- **THEN** 路由函数正常执行

#### Scenario: Token 缺失或无效
- **WHEN** 请求未携带 Authorization 头或 Token 过期/无效
- **THEN** MUST 返回 `{ "code": 401, "message": "Authentication required" }` 和 401 状态码

#### Scenario: Token 过期
- **WHEN** access_token 已过期
- **THEN** MUST 返回 `{ "code": 401, "message": "Token expired" }`

### Requirement: 登录 API
后端 SHALL 提供 `POST /api/v1/auth/login` 端点，接受 username 和 password，返回 JWT Token 对和用户信息。

#### Scenario: 登录成功
- **WHEN** 用户提供正确的 username 和 password
- **THEN** MUST 返回 `{ "code": 200, "data": { "access_token", "refresh_token", "user" } }`
- **THEN** user 对象 MUST 包含 `id`、`username`、`email`、`role`

#### Scenario: 登录失败
- **WHEN** 用户提供错误的 username 或 password
- **THEN** MUST 返回 `{ "code": 401, "message": "Invalid username or password" }`

### Requirement: 注册 API
后端 SHALL 提供 `POST /api/v1/auth/register` 端点，接受 username、email、password，创建用户并返回 JWT Token。

#### Scenario: 注册成功
- **WHEN** 用户提供有效的 username（3-64 字符）、email、password（>=8 字符含大小写和数字）
- **THEN** MUST 创建用户并返回 `{ "code": 201, "data": { "access_token", "refresh_token", "user" } }`

#### Scenario: 用户名已存在
- **WHEN** username 已被注册
- **THEN** MUST 返回 `{ "code": 409, "message": "Username already exists" }`

### Requirement: Token 刷新 API
后端 SHALL 提供 `POST /api/v1/auth/refresh` 端点，接受 refresh_token，返回新的 access_token。

#### Scenario: 刷新成功
- **WHEN** 前端发送有效的 refresh_token
- **THEN** MUST 返回 `{ "code": 200, "data": { "access_token": "<new_jwt>" } }`

#### Scenario: refresh_token 无效或过期
- **WHEN** refresh_token 无效或已过期
- **THEN** MUST 返回 `{ "code": 401, "message": "Invalid refresh token" }`

### Requirement: 前端 Axios 拦截器
前端 Axios 实例 SHALL 配置请求拦截器（自动添加 Authorization 头）和响应拦截器（401 自动刷新 Token）。

#### Scenario: 请求自动带 Token
- **WHEN** 前端发送 API 请求且 auth store 中有 access_token
- **THEN** Axios 拦截器 MUST 自动添加 `Authorization: Bearer <token>` 头

#### Scenario: 401 自动刷新
- **WHEN** API 返回 401 且 auth store 中有 refresh_token
- **THEN** 拦截器 MUST 自动调用 `/api/v1/auth/refresh`
- **THEN** 成功后 MUST 用新 Token 重试原始请求
- **THEN** 刷新失败 MUST 清除 auth store 并跳转登录页
