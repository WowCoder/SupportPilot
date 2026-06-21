## MODIFIED Requirements

### Requirement: Auth 页面居中布局
Login 和 Register 页面 SHALL 使用 Vue 组件渲染居中布局，内容包裹在 `.auth-card` 卡片中，最大宽度 400px，不显示 topnav。

#### Scenario: Login 页面布局
- **WHEN** 用户访问 `/login`（Vue Router 路由）
- **THEN** 页面 MUST 显示居中白色卡片，包含 logo-dot + "SupportPilot" 标题 + "欢迎回来，请登录您的账户" 副标题
- **THEN** 页面 MUST NOT 包含 topnav 组件
- **THEN** 页面 MUST 使用 Vue `<script setup>` 组件实现，非 Jinja2 模板

#### Scenario: Register 页面布局
- **WHEN** 用户访问 `/register`（Vue Router 路由）
- **THEN** 页面 MUST 显示居中白色卡片，包含 logo-dot + "SupportPilot" 标题 + "创建您的账户，开始使用智能客服" 副标题
- **THEN** 页面 MUST NOT 包含 topnav 组件

### Requirement: Login 表单
Login 页面 SHALL 使用 Element Plus `el-form` 组件，包含 Username 和 Password 两个输入字段、错误提示区域、"登录" 提交按钮。不再使用 CSRF token 和 Flash messages。

#### Scenario: Login 表单字段
- **WHEN** Login 页面加载
- **THEN** Username `el-input` MUST 有 placeholder "请输入用户名" 和 autofocus
- **THEN** Password `el-input` MUST 有 placeholder "请输入密码" 和 show-password 切换
- **THEN** 表单 MUST NOT 包含 CSRF token 隐藏字段
- **THEN** 提交按钮 MUST 为 `el-button type="primary"` 显示 "登录" 文字

#### Scenario: Login 错误提示
- **WHEN** 登录失败（API 返回错误）
- **THEN** 错误信息 MUST 通过 `el-message.error` 或卡片上方 `el-alert` 显示
- **THEN** MUST NOT 使用 Flask Flash messages

### Requirement: Register 表单
Register 页面 SHALL 使用 Element Plus `el-form` 组件，包含 Username、Email、Password 三个字段、客户端验证、AJAX 提交。

#### Scenario: Register 表单字段
- **WHEN** Register 页面加载
- **THEN** Username `el-input` MUST 有 placeholder "请输入用户名" 和 autofocus
- **THEN** Email `el-input` MUST 有 placeholder "请输入邮箱"
- **THEN** Password `el-input` MUST 有 placeholder "请输入密码" 和 `show-password`
- **THEN** Password 下方 MUST 显示提示文字 "密码至少需要 8 个字符，包含大小写字母和数字"

#### Scenario: Register 客户端验证
- **WHEN** 用户提交表单
- **THEN** `el-form` validation rules MUST 验证 Username 长度 3-64 字符
- **THEN** MUST 验证 Email 格式有效性
- **THEN** MUST 验证 Password 长度 >= 8 + 包含大小写字母和数字
- **THEN** 验证失败时 MUST 在对应 `el-form-item` 下方显示红色错误信息
- **THEN** 提交时 MUST 通过 Axios 发送 JSON（非表单 POST）

#### Scenario: Register API 响应
- **WHEN** 注册成功（API 返回 201）
- **THEN** MUST 自动登录（存储 Token）并跳转到首页
- **WHEN** 注册失败
- **THEN** MUST 显示 `el-message.error` 错误信息
- **THEN** 提交按钮 MUST 恢复可用状态

### Requirement: Auth 页脚链接
Auth 页面 SHALL 在卡片底部显示导航链接（Login → "还没有账户？立即注册"、Register → "已有账户？立即登录"），使用 `router-link` 跳转。

#### Scenario: Login 页脚
- **WHEN** Login 页面加载
- **THEN** 卡片底部 MUST 显示 `<router-link to="/register">` "还没有账户？立即注册"

#### Scenario: Register 页脚
- **WHEN** Register 页面加载
- **THEN** 卡片底部 MUST 显示 `<router-link to="/login">` "已有账户？立即登录"

## REMOVED Requirements

### Requirement: 原型功能差异 — 原型缺失的现有功能
**Reason**: 前端完全重写为 Vue 组件，CSRF token、Flash messages 等概念在新架构中不再适用
**Migration**: CSRF 保护在纯 API + JWT 认证下不再需要；Flash messages 替换为 Element Plus 的 el-message/el-alert 组件

### Requirement: 原型功能差异 — 原型有但当前不存在
**Reason**: 与新 Vue 实现的组件架构无关
**Migration**: Vue 实现时以现有功能为基准，不引入原型中的额外字段
