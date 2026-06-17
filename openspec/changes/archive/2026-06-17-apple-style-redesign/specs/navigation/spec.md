# Navigation Specification

## ADDED Requirements

### Requirement: Apple 风格顶部导航栏

系统 SHALL 使用固定在顶部的半透明玻璃导航栏，如 DESIGN.md 所定义。

**设计要求:**
- 位置：固定在页面顶部 (position: fixed/top: 0)
- 背景：`rgba(0, 0, 0, 0.8)`
- 模糊效果：`backdrop-filter: saturate(180%) blur(20px)`
- 高度：48px
- Logo 尺寸：17x48px viewport

#### Scenario: 导航栏固定
- **WHEN** 用户滚动页面
- **THEN** 导航栏应保持在顶部可见

#### Scenario: 玻璃效果
- **WHEN** 页面内容滚动到导航栏下方
- **THEN** 内容应模糊可见透过导航栏

### Requirement: 导航栏 Logo

系统 SHALL 在导航栏左侧显示品牌 Logo。

**设计要求:**
- 位置：导航栏左侧或居中
- 内容：SVG logo 或图标 + 文字
- 颜色：#ffffff

#### Scenario: Logo 点击
- **WHEN** 用户点击 Logo
- **THEN** 应跳转到首页

### Requirement: 导航栏菜单

系统 SHALL 在导航栏显示导航菜单。

**设计要求:**
- 文字大小：12px
- 字重：400 (Regular)
- 颜色：#ffffff
- 悬停效果：underline on hover

#### Scenario: 菜单项悬停
- **WHEN** 用户悬停在菜单项上
- **THEN** 应显示下划线

### Requirement: 移动端导航

系统 SHALL 在小屏幕上显示折叠的移动导航。

**设计要求:**
- 断点：根据 DESIGN.md 响应式断点
- 汉堡菜单：右侧显示
- 展开方式：全屏覆盖菜单

#### Scenario: 移动端菜单展开
- **WHEN** 用户点击汉堡菜单
- **THEN** 菜单应展开为全屏覆盖
