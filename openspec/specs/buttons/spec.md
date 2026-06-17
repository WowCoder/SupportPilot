# Buttons Specification

## ADDED Requirements

### Requirement: Primary Blue 按钮

系统 SHALL 使用 Apple Blue 主按钮。

**设计要求:**
- 背景：#0071e3 (Apple Blue)
- 文字：#ffffff
- 内边距：8px 15px
- 圆角：8px
- 边框：1px solid transparent
- 字体：SF Pro Text, 17px, weight 400
- Focus: 2px solid #0071e3 outline

#### Scenario: Primary 按钮渲染
- **WHEN** 页面加载主按钮
- **THEN** 按钮应有 #0071e3 背景和 8px 圆角

#### Scenario: Primary 按钮悬停
- **WHEN** 用户悬停在主按钮上
- **THEN** 背景色应稍微变亮

### Requirement: Primary Dark 按钮

系统 SHALL 使用深色主按钮。

**设计要求:**
- 背景：#1d1d1f
- 文字：#ffffff
- 内边距：8px 15px
- 圆角：8px

#### Scenario: Dark 按钮渲染
- **WHEN** 页面加载深色按钮
- **THEN** 按钮应有 #1d1d1f 背景

### Requirement: Pill Link 按钮

系统 SHALL 使用胶囊形链接按钮。

**设计要求:**
- 背景：透明
- 文字：#0066cc (浅色背景) 或 #2997ff (深色背景)
- 圆角：980px (完整胶囊形)
- 边框：1px solid #0066cc
- 字体：SF Pro Text, 14px-17px
- 悬停：underline decoration

#### Scenario: Pill 链接渲染
- **WHEN** 页面加载 "Learn more" 链接
- **THEN** 应有透明背景、980px 圆角和边框

#### Scenario: Pill 链接悬停
- **WHEN** 用户悬停在 Pill 链接上
- **THEN** 应显示下划线

### Requirement: Filter/Search 按钮

系统 SHALL 使用筛选/搜索按钮样式。

**设计要求:**
- 背景：#fafafc
- 文字：rgba(0, 0, 0, 0.8)
- 内边距：0px 14px
- 圆角：11px
- 边框：3px solid rgba(0, 0, 0, 0.04)
- Focus: 2px solid #0071e3 outline

#### Scenario: Search 按钮渲染
- **WHEN** 页面加载搜索框
- **THEN** 应有 #fafafc 背景和 11px 圆角

### Requirement: Media Control 按钮

系统 SHALL 使用媒体控制按钮样式。

**设计要求:**
- 背景：rgba(210, 210, 215, 0.64)
- 文字：rgba(0, 0, 0, 0.48)
- 圆角：50% (圆形)
- 激活：scale(0.9)
- Focus: 2px solid #0071e3 outline, 白色背景

#### Scenario: Media 按钮渲染
- **WHEN** 页面加载播放/暂停按钮
- **THEN** 应有圆形外观和半透明背景
