# Cards Specification

## ADDED Requirements

### Requirement: Apple 风格卡片容器

系统 SHALL 使用 Apple 风格的卡片容器设计。

**设计要求:**
- 背景：#f5f5f7 (浅色) 或 #272729-#2a2a2d (深色)
- 圆角：5px-8px
- 边框：无（Apple 极少使用边框）
- 内容：居中，充足的内边距

#### Scenario: 卡片渲染
- **WHEN** 页面加载卡片组件
- **THEN** 卡片应有 #f5f5f7 背景和 8px 圆角

### Requirement: 卡片阴影

系统 SHALL 为 elevated 卡片使用 Apple 风格的阴影。

**阴影定义:**
```css
box-shadow: rgba(0, 0, 0, 0.22) 3px 5px 30px 0px;
```

#### Scenario: 卡片阴影
- **WHEN** 渲染 elevated 卡片
- **THEN** 应使用上述柔和阴影

### Requirement: 卡片头部

系统 SHALL 支持可选的卡片头部区域。

**设计要求:**
- 标题字体：SF Pro Display, 21px 或 28px
- 字重：400 或 700
- 颜色：#1d1d1f (浅背景) 或 #ffffff (深背景)

#### Scenario: 卡片标题
- **WHEN** 卡片有标题
- **THEN** 标题应以 SF Pro Display 显示

### Requirement: 卡片内容区

系统 SHALL 支持卡片主体内容区域。

**设计要求:**
- 正文字体：SF Pro Text, 14px 或 17px
- 颜色：rgba(0, 0, 0, 0.8) 或 #ffffff

#### Scenario: 卡片内容
- **WHEN** 卡片有内容
- **THEN** 内容应以适当的字体和颜色显示

### Requirement: 卡片链接

系统 SHALL 使用 Apple 风格的卡片内链接。

**设计要求:**
- "Learn more" 和 "Shop" 链接对
- 颜色：#0066cc (浅背景) 或 #2997ff (深背景)
- 可选 Pill 形状容器 (980px 圆角)

#### Scenario: 卡片链接
- **WHEN** 卡片有操作链接
- **THEN** 应使用 "Learn more" 和 "Shop" 链接对
