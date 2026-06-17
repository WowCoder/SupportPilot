# Forms Specification

## ADDED Requirements

### Requirement: Apple 风格输入框

系统 SHALL 使用 Apple 风格的输入框设计。

**设计要求:**
- 背景：#ffffff
- 边框：根据上下文（Filter button 为 3px solid rgba(0, 0, 0, 0.04)）
- 圆角：11px (搜索/筛选) 或 8px (标准输入)
- 内边距：根据上下文
- 字体：SF Pro Text, 15px-17px
- Focus: 2px solid #0071e3 outline

#### Scenario: 输入框渲染
- **WHEN** 页面加载输入框
- **THEN** 输入框应有适当的圆角和边框

#### Scenario: 输入框 Focus
- **WHEN** 用户聚焦到输入框
- **THEN** 应显示 2px #0071e3 轮廓

### Requirement: 输入框占位符

系统 SHALL 使用 Apple 风格的占位符样式。

**设计要求:**
- 颜色：rgba(0, 0, 0, 0.48) 或类似灰色
- 字体风格：Regular (400)

#### Scenario: 占位符显示
- **WHEN** 输入框为空且未聚焦
- **THEN** 应显示灰色占位符文本

### Requirement: 表单标签

系统 SHALL 使用 Apple 风格的标签样式。

**设计要求:**
- 字体：SF Pro Text
- 字重：Medium (500) 或根据上下文
- 颜色：#1d1d1f 或 #ffffff (深色背景)

#### Scenario: 标签渲染
- **WHEN** 表单有标签
- **THEN** 标签应以 SF Pro Text 显示

### Requirement: 表单帮助文本

系统 SHALL 支持帮助文本显示。

**设计要求:**
- 字体：SF Pro Text, 12px-14px
- 颜色：rgba(0, 0, 0, 0.8) 或次要文本色

#### Scenario: 帮助文本显示
- **WHEN** 表单字段有帮助信息
- **THEN** 帮助文本应以次要颜色显示

### Requirement: 表单错误状态

系统 SHALL 支持输入错误状态显示。

**设计要求:**
- 使用 Focus 颜色系统或标准错误色
- 清晰可见的错误提示

#### Scenario: 输入错误显示
- **WHEN** 输入验证失败
- **THEN** 应有清晰的错误指示
