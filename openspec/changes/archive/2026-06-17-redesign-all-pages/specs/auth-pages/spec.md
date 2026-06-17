## ADDED Requirements

### Requirement: Auth 页面居中布局
Login 和 Register 页面 SHALL 使用 `.auth-page` 全屏居中布局，内容包裹在 `.auth-card` 卡片中，最大宽度 400px，不显示 topnav。

#### Scenario: Login 页面布局
- **WHEN** 用户访问 `/auth/login`
- **THEN** 页面 MUST 显示居中白色卡片，包含 logo-dot + "SupportPilot" 标题 + "欢迎回来，请登录您的账户" 副标题
- **THEN** 页面 MUST NOT 包含 `.topnav` 元素

#### Scenario: Register 页面布局
- **WHEN** 用户访问 `/auth/register`
- **THEN** 页面 MUST 显示居中白色卡片，包含 logo-dot + "SupportPilot" 标题 + "创建您的账户，开始使用智能客服" 副标题
- **THEN** 页面 MUST NOT 包含 `.topnav` 元素

### Requirement: Login 表单
Login 页面 SHALL 包含 Username 和 Password 两个输入字段、CSRF token、Flash messages 区域、"登录" 提交按钮（全宽）。

#### Scenario: Login 表单字段
- **WHEN** Login 页面加载
- **THEN** Username 输入框 MUST 有 placeholder "请输入用户名" 和 autofocus
- **THEN** Password 输入框 MUST 有 placeholder "请输入密码"
- **THEN** 表单 MUST 包含隐藏的 `csrf_token` 字段
- **THEN** 提交按钮 MUST 显示 "登录" 文字和 sign-in 图标

#### Scenario: Login Flash 消息
- **WHEN** 后端返回 flash 消息（如登录失败）
- **THEN** Flash 消息 MUST 显示在 auth-card 上方（max-width: 450px）
- **THEN** Error 消息 MUST 显示红色感叹号图标
- **THEN** Success 消息 MUST 显示绿色对勾图标

### Requirement: Register 表单
Register 页面 SHALL 包含 Username、Email、Password 三个字段、CSRF token、客户端 JS 验证。

#### Scenario: Register 表单字段
- **WHEN** Register 页面加载
- **THEN** Username 输入框 MUST 有 placeholder "请输入用户名" 和 autofocus
- **THEN** Email 输入框 MUST 有 placeholder "请输入邮箱"
- **THEN** Password 输入框 MUST 有 placeholder "请输入密码"
- **THEN** Password 下方 MUST 显示提示文字 "密码至少需要 8 个字符，包含大小写字母和数字"
- **THEN** 每个字段下方 MUST 有对应的 `.form-error` 元素

#### Scenario: Register 客户端验证
- **WHEN** 用户提交表单
- **THEN** Username MUST 验证长度为 3-64 字符
- **THEN** Email MUST 验证格式有效性
- **THEN** Password MUST 验证长度 >= 8 + 包含大小写字母和数字
- **THEN** 验证失败时 MUST 在对应字段下方显示红色错误信息
- **THEN** 提交时 MUST 使用 AJAX（`X-Requested-With: XMLHttpRequest`）发送表单

#### Scenario: Register AJAX 响应
- **WHEN** 注册成功（`data.success === true`）
- **THEN** 页面 MUST 跳转到 `data.redirect` 或 `/login`
- **WHEN** 注册失败
- **THEN** Flash 区域 MUST 显示错误信息
- **THEN** 提交按钮 MUST 恢复可用状态

### Requirement: Auth 页脚链接
Auth 页面 SHALL 在卡片底部显示导航链接（Login → "还没有账户？立即注册"、Register → "已有账户？立即登录"）。

#### Scenario: Login 页脚
- **WHEN** Login 页面加载
- **THEN** 卡片底部 MUST 显示 "还没有账户？立即注册" 链接到 Register 页面

#### Scenario: Register 页脚
- **WHEN** Register 页面加载
- **THEN** 卡片底部 MUST 显示 "已有账户？立即登录" 链接到 Login 页面

### Requirement: 原型功能差异 — 原型缺失的现有功能
以下现有功能在设计原型中未体现，实现时 MUST 保留：
- Login 使用 **Username**（非 Email）作为登录字段
- CSRF token 隐藏字段
- Flash messages 显示区域（登录失败/成功等反馈）
- Register 的 JS 客户端验证（用户名 3-64 字符、邮箱格式、密码强度）
- Register 的 AJAX 表单提交（非传统 POST）
- 表单字段上的 `.form-error` 实时错误显示

### Requirement: 原型功能差异 — 原型有但当前不存在
以下原型功能当前不存在，暂不保留：
- Login 使用 Email 而非 Username — 保持当前 Username 方式
- Register 的 Full Name 和 Company 字段 — 当前注册表单无此字段，不新增
- 原型静态 HTML 的 mock form action 和预设值 — 使用真实后端端点
