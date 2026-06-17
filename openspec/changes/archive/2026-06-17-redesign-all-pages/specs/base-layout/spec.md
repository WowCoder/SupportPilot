## ADDED Requirements

### Requirement: Topnav 顶部导航
所有已登录页面 SHALL 使用 `.topnav` 顶部导航栏（sticky、毛玻璃背景），包含左侧 brand 标识（logo-dot + "SupportPilot" 文字）、导航链接、右侧用户信息和头像。

#### Scenario: Topnav 渲染
- **WHEN** 用户登录后访问任何页面
- **THEN** topnav MUST 固定在页面顶部（`position: sticky; top: 0; z-index: 100`）
- **THEN** topnav MUST 有毛玻璃效果（`backdrop-filter: saturate(180%) blur(20px)`）
- **THEN** brand 区域 MUST 显示蓝色圆点 + "SupportPilot" 文字

#### Scenario: 导航链接高亮
- **WHEN** 用户当前在某个页面
- **THEN** 对应导航链接 MUST 带有 `.active` class（深色文字 + 半透明背景）

### Requirement: 用户信息显示
Topnav 右侧 SHALL 显示用户名/公司和用户头像（`.topnav-avatar`），根据用户角色显示不同信息。

#### Scenario: 普通用户 topnav
- **WHEN** 普通用户登录
- **THEN** topnav 右侧 MUST 显示公司名 + 用户头像（首字母缩写）

#### Scenario: 技术支持 topnav
- **WHEN** 技术支持人员登录
- **THEN** topnav 右侧 MUST 显示在线状态 badge（绿点 + "Online"）+ 用户头像

### Requirement: 导航链接按角色区分
Topnav 导航链接 SHALL 根据用户角色显示不同菜单项：普通用户显示 Dashboard / Messages / Documents / FAQ，技术支持显示 Dashboard / Queue / Documents / FAQ。

#### Scenario: 普通用户导航
- **WHEN** 普通用户登录
- **THEN** topnav 链接 MUST 包含 Dashboard、Messages、Documents、FAQ

#### Scenario: 技术支持导航
- **WHEN** 技术支持登录
- **THEN** topnav 链接 MUST 包含 Dashboard、Queue、Documents、FAQ

### Requirement: Page Content 容器
页面主要内容 SHALL 使用 `.page-content` 容器，限制最大宽度 1080px，水平居中，上下内边距 28px/48px。

#### Scenario: Page content 渲染
- **WHEN** 页面在宽屏（>1080px）下渲染
- **THEN** 内容 MUST 限制在 1080px 宽度内水平居中
- **THEN** 左右 MUST 自动留白

### Requirement: Flash Messages
Flash 消息 SHALL 保留在 page-content 顶部，使用 `.flash-messages` 容器，不同类型的消息显示对应图标和颜色。

#### Scenario: Success flash
- **WHEN** 后端返回 success category flash 消息
- **THEN** 消息 MUST 显示绿色对勾图标
- **THEN** 消息 MUST 以 success 样式渲染

#### Scenario: Error flash
- **WHEN** 后端返回 error/danger category flash 消息
- **THEN** 消息 MUST 显示红色感叹号图标
