## Why

当前 SupportPilot 的界面设计较为普通，缺乏现代感和专业感。采用 DESIGN.md 中定义的 Apple 设计语言可以提升产品的视觉品质，给用户更专业、简洁、优雅的使用体验，增强用户对产品技术能力的信任感。

## What Changes

- **整体视觉风格重构**：采用 DESIGN.md 定义的 Apple 设计语言
- **导航栏升级**：采用 Apple 风格的顶部半透明玻璃导航（`rgba(0,0,0,0.8)` + `backdrop-filter: blur(20px)`）
- **卡片设计**：采用 Apple 风格的卡片，柔和阴影（`rgba(0, 0, 0, 0.22) 3px 5px 30px 0px`）
- **按钮样式**：采用 Apple 风格的按钮（Apple Blue `#0071e3`、Pill 形 `980px` 圆角）
- **表单输入框**：采用 Apple 风格的输入框（`11px` 圆角、柔和边框）
- **排版优化**：采用 SF Pro 字体栈，优化的字重和行高（负字母间距）
- **颜色系统**：采用 Apple 风格的配色（纯黑 `#000000`、浅灰 `#f5f5f7`、Apple Blue `#0071e3`）
- **间距系统**：基于 8px 网格的 Apple 间距系统
- **动画效果**：添加 Apple 风格的微动画（平滑过渡、弹性效果）
- **响应式优化**：确保在所有设备上都有 Apple 级别的体验

## Capabilities

### New Capabilities

- `design-tokens`: Apple 风格的设计令牌系统（颜色、字体、间距、圆角、阴影）
- `navigation`: Apple 风格的顶部半透明导航栏组件
- `cards`: Apple 风格的卡片组件
- `buttons`: Apple 风格的按钮组件（Primary Blue、Pill Link、Filter）
- `forms`: Apple 风格的表单组件
- `typography`: Apple 风格的排版系统（SF Pro、负字母间距）
- `animations`: Apple 风格的微动画系统

### Modified Capabilities

（无 - 现有功能需求不变，仅视觉风格变化）

## Impact

- **影响文件**：
  - `static/css/style.css` - 完全重构
  - `templates/base.html` - 导航栏和 footer 更新
  - `templates/*.html` - 所有页面模板应用新样式
  
- **依赖**：
  - 字体：SF Pro Display/Text（回退到 Helvetica Neue, Arial）
  - 图标库保持 Font Awesome 6，但使用风格一致的图标

- **浏览器兼容**：
  - 现代浏览器（Chrome、Safari、Firefox、Edge）
  - 保持与现有相同的兼容性水平

- **无破坏性变更**：
  - 所有现有功能保持不变
  - 仅视觉风格变化，不影响后端逻辑
