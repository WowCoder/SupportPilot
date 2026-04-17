# Typography Specification

## ADDED Requirements

### Requirement: Apple 风格字体栈

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

#### Scenario: Display 字体使用
- **WHEN** 字体尺寸 >= 20px
- **THEN** 应使用 SF Pro Display

#### Scenario: Text 字体使用
- **WHEN** 字体尺寸 < 20px
- **THEN** 应使用 SF Pro Text

### Requirement: 标题层级

系统 SHALL 使用 DESIGN.md 定义的标题层级。

**标题样式:**
| Role | Font | Size | Weight | Line Height | Letter Spacing |
|------|------|------|--------|-------------|----------------|
| Display Hero | SF Pro Display | 56px | 600 | 1.07 | -0.28px |
| Section Heading | SF Pro Display | 40px | 600 | 1.10 | normal |
| Tile Heading | SF Pro Display | 28px | 400 | 1.14 | 0.196px |
| Card Title | SF Pro Display | 21px | 700 | 1.19 | 0.231px |
| Sub-heading | SF Pro Display | 21px | 400 | 1.19 | 0.231px |

#### Scenario: H1 渲染
- **WHEN** 页面有 H1 标题
- **THEN** 应以 56px SF Pro Display weight 600 显示，行高 1.07，字母间距 -0.28px

#### Scenario: H2 渲染
- **WHEN** 页面有 H2 标题
- **THEN** 应以 40px SF Pro Display weight 600 显示，行高 1.10

### Requirement: 正文文本

系统 SHALL 使用 Apple 风格的正文样式。

**正文样式:**
- 字体：SF Pro Text, 17px
- 字重：400
- 行高：1.47
- 字母间距：-0.374px
- 颜色：#1d1d1f (浅背景) 或 #ffffff (深背景)

#### Scenario: 正文渲染
- **WHEN** 页面显示正文
- **THEN** 应以 17px SF Pro Text 显示，字母间距 -0.374px

### Requirement: 次要文本

系统 SHALL 使用灰色显示次要文本。

**样式定义:**
- 颜色：rgba(0, 0, 0, 0.8) (浅背景) 或 #ffffff (深背景)
- 字体大小：可比正文小

#### Scenario: 次要文本显示
- **WHEN** 显示描述性或辅助文本
- **THEN** 应以 rgba(0, 0, 0, 0.8) 显示

### Requirement: 链接样式

系统 SHALL 使用 Apple 风格的链接样式。

**链接样式:**
- 颜色：#0066cc (浅色背景)
- 颜色：#2997ff (深色背景)
- 悬停：underline decoration
- 字体：SF Pro Text, 14px
- 字母间距：-0.224px

#### Scenario: 链接渲染
- **WHEN** 页面有链接
- **THEN** 链接应为 #0066cc (浅背景) 或 #2997ff (深背景)

#### Scenario: 链接悬停
- **WHEN** 用户悬停在链接上
- **THEN** 应显示下划线

### Requirement: 负字母间距

系统 SHALL 在所有文本尺寸应用负字母间距。

**字母间距定义:**
- 56px: -0.28px
- 17px: -0.374px
- 14px: -0.224px
- 12px: -0.12px
- 10px: -0.08px

#### Scenario: 正文字母间距
- **WHEN** 渲染正文
- **THEN** 字母间距应为 -0.374px
