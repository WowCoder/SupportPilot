# Animations Specification

## ADDED Requirements

### Requirement: Apple 风格过渡效果

系统 SHALL 使用平滑的过渡效果。

**过渡定义:**
- 快速过渡：150ms ease-out（按钮、小元素）
- 标准过渡：200ms ease-out（卡片、中等元素）
- 慢速过渡：300ms cubic-bezier(0.4, 0, 0.2, 1)（模态框、大元素）

#### Scenario: 按钮颜色过渡
- **WHEN** 用户悬停在按钮上
- **THEN** 颜色变化应在 150ms 内平滑完成

### Requirement: 悬停效果

系统 SHALL 为交互元素添加悬停效果。

**效果定义:**
- 按钮：背景色变化
- Pill 链接：underline decoration
- 导航链接：underline on hover

#### Scenario: Pill 链接悬停
- **WHEN** 用户悬停在 "Learn more" 链接上
- **THEN** 应显示下划线

### Requirement: 模态框动画

系统 SHALL 使用平滑的模态框进入/退出动画。

**动画定义:**
- 进入：从上方滑入 + 透明度渐变
- 退出：向上升起 + 透明度渐变
- 持续时间：300ms
- 缓动函数：cubic-bezier(0.4, 0, 0.2, 1)

#### Scenario: 模态框打开
- **WHEN** 模态框被触发打开
- **THEN** 应从上方平滑滑入

### Requirement: 按钮点击反馈

系统 SHALL 为按钮提供点击反馈。

**反馈定义:**
- Media Control: scale(0.9)
- 背景色变化（Active 状态）

#### Scenario: Media 按钮点击
- **WHEN** 用户点击播放/暂停按钮
- **THEN** 按钮应缩小到 0.9 倍

### Requirement: 减少动画偏好

系统 SHALL 尊重用户的减少动画偏好设置。

**设计要求:**
- 检测：prefers-reduced-motion: reduce
- 行为：禁用或简化动画

#### Scenario: 减少动画模式
- **WHEN** 用户系统设置了减少动画
- **THEN** 所有动画应禁用或简化
