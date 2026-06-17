# Design Tokens Specification

## ADDED Requirements

### Requirement: Apple 风格颜色系统

系统 SHALL 使用 DESIGN.md 定义的颜色令牌系统。

**主色:**
- Apple Blue: #0071e3 (Primary CTA, Focus Ring)
- Link Blue: #0066cc (浅色背景上的链接)
- Bright Blue: #2997ff (深色背景上的链接)

**背景色:**
- Pure Black: #000000 (Hero 区域深色背景)
- Light Gray: #f5f5f7 (浅色区域背景)
- Near Black: #1d1d1f (浅色背景上的主要文本)

**暗色表面:**
- Dark Surface 1: #272729
- Dark Surface 2: #262628
- Dark Surface 3: #28282a
- Dark Surface 4: #2a2a2d
- Dark Surface 5: #242426

**按钮状态:**
- Button Active: #ededf2
- Button Default Light: #fafafc
- Overlay: rgba(210, 210, 215, 0.64)

#### Scenario: 主按钮颜色
- **WHEN** 用户看到主按钮
- **THEN** 按钮背景色应为 #0071e3

#### Scenario: 背景颜色
- **WHEN** 页面加载时
- **THEN** 浅色区域背景应为 #f5f5f7，深色区域为 #000000

### Requirement: 字体系统

系统 SHALL 使用 SF Pro 字体栈。

**字体定义:**
```css
/* Display (20px+) */
font-family: 'SF Pro Display', 'SF Pro Icons', 
             'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;

/* Body (<20px) */
font-family: 'SF Pro Text', 'SF Pro Icons', 
             'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
```

**字重:**
- Light: 300 (仅用于大尺寸装饰文本)
- Regular: 400 (正文字重)
- Medium: 500
- Semibold: 600 (标题字重)
- Bold: 700 (罕见的粗体)

#### Scenario: 字体渲染
- **WHEN** 页面在 Apple 设备上渲染
- **THEN** 应使用 SF Pro 字体

#### Scenario: 字体回退
- **WHEN** 设备不支持 SF Pro
- **THEN** 应回退到 Helvetica Neue, Arial

### Requirement:  typography 层级

系统 SHALL 使用 DESIGN.md 定义的排版层级。

| Role | Font | Size | Weight | Line Height | Letter Spacing |
|------|------|------|--------|-------------|----------------|
| Display Hero | SF Pro Display | 56px | 600 | 1.07 | -0.28px |
| Section Heading | SF Pro Display | 40px | 600 | 1.10 | normal |
| Tile Heading | SF Pro Display | 28px | 400 | 1.14 | 0.196px |
| Card Title | SF Pro Display | 21px | 700 | 1.19 | 0.231px |
| Sub-heading | SF Pro Display | 21px | 400 | 1.19 | 0.231px |
| Body | SF Pro Text | 17px | 400 | 1.47 | -0.374px |
| Body Emphasis | SF Pro Text | 17px | 600 | 1.24 | -0.374px |
| Button | SF Pro Text | 17px | 400 | 2.41 | normal |
| Link | SF Pro Text | 14px | 400 | 1.43 | -0.224px |
| Caption | SF Pro Text | 14px | 400 | 1.29 | -0.224px |
| Micro | SF Pro Text | 12px | 400 | 1.33 | -0.12px |
| Nano | SF Pro Text | 10px | 400 | 1.47 | -0.08px |

#### Scenario: H1 渲染
- **WHEN** 页面有 H1 标题
- **THEN** 应以 56px SF Pro Display weight 600 显示，行高 1.07

#### Scenario: 正文字体
- **WHEN** 页面显示正文
- **THEN** 应以 17px SF Pro Text weight 400 显示，字母间距 -0.374px

### Requirement: 间距系统

系统 SHALL 使用基于 8px 的 Apple 间距系统。

**间距令牌:**
- 2px, 4px, 5px, 6px, 7px, 8px, 9px, 10px, 11px
- 14px, 15px, 17px, 20px, 24px

**按钮内边距:**
- Primary/Dark: 8px 15px
- Filter/Search: 0px 14px

#### Scenario: 按钮内边距
- **WHEN** 渲染标准按钮
- **THEN** 内边距应为 8px 15px

### Requirement: 圆角系统

系统 SHALL 使用 DESIGN.md 定义的圆角。

**圆角令牌:**
- Micro (5px): 小容器、链接标签
- Standard (8px): 按钮、产品卡片
- Comfortable (11px): 搜索框、筛选按钮
- Large (12px): 功能面板、生活方式图片容器
- Full Pill (980px): CTA 链接 ("Learn more", "Shop")
- Circle (50%): 媒体控制按钮

#### Scenario: 按钮圆角
- **WHEN** 渲染按钮
- **THEN** 圆角应为 8px

#### Scenario: Pill 链接圆角
- **WHEN** 渲染 "Learn more" 链接
- **THEN** 圆角应为 980px（胶囊形）

### Requirement: 阴影系统

系统 SHALL 使用单一的柔和阴影。

**阴影定义:**
```css
box-shadow: rgba(0, 0, 0, 0.22) 3px 5px 30px 0px;
```

#### Scenario: 卡片阴影
- **WHEN** 渲染 elevated 卡片
- **THEN** 应使用 `rgba(0, 0, 0, 0.22) 3px 5px 30px 0px`

### Requirement: 玻璃导航效果

系统 SHALL 使用 Apple 风格的半透明玻璃导航。

**定义:**
```css
background: rgba(0, 0, 0, 0.8);
backdrop-filter: saturate(180%) blur(20px);
```

#### Scenario: 导航栏渲染
- **WHEN** 页面加载导航栏
- **THEN** 应有半透明黑色背景和模糊效果
