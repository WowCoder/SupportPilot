## Context

**Background:**
SupportPilot 当前使用自定义的设计系统，基于 CSS 自定义属性（Design Tokens）。虽然功能完整，但视觉风格较为普通，缺乏现代感和专业感。

**DESIGN.md 规范:**
根目录下的 DESIGN.md 已定义了完整的 Apple 设计系统，包括：
- 颜色系统（纯黑 `#000000`、浅灰 `#f5f5f7`、Apple Blue `#0071e3`）
- 字体系统（SF Pro Display/Text，负字母间距）
- 组件样式（按钮、卡片、导航）
- 布局原则（8px 基准间距、980px 内容宽度）
- 深度与阴影（玻璃导航、柔和阴影）

**Constraints:**
- 所有设计决策必须参考 DESIGN.md
- 保持 Flask 模板架构不变
- 保持所有后端逻辑不变
- 保持 Font Awesome 图标库
- 兼容现有浏览器支持范围

## Goals / Non-Goals

**Goals:**
1. 实现 Apple 风格的视觉设计系统
2. 重构所有 CSS 组件采用 Apple 设计语言
3. 更新导航栏采用 Apple 风格的半透明顶部导航
4. 优化排版系统采用 Apple 风格的字重和间距
5. 添加 Apple 风格的微动画和过渡效果
6. 确保响应式设计在所有设备上表现一致

**Non-Goals:**
1. 不改变任何后端逻辑或 API
2. 不改变功能或用户交互流程
3. 不引入新的 JavaScript 框架
4. 不改变数据库结构
5. 不改变现有的模板结构（仅样式类名和 HTML 结构微调）

## Decisions

### 1. 颜色系统设计

**Decision:** 采用 DESIGN.md 定义的颜色系统

**颜色定义:**
- Primary: #0071e3 (Apple Blue) - 仅用于交互元素
- Background Light: #f5f5f7 (浅灰背景)
- Background Dark: #000000 (纯黑背景)
- Text Primary Light: #1d1d1f (近黑深灰)
- Text Secondary: rgba(0, 0, 0, 0.8)
- Text Dark BG: #ffffff
- Link Light: #0066cc
- Link Dark: #2997ff

**Rationale:**
DESIGN.md 定义了完整的 Apple 颜色系统，二元背景（黑/浅灰）+ 单一强调色（Apple Blue）。

### 2. 字体系统

**Decision:** 使用 SF Pro 字体栈

**Font Stack:**
```css
font-family: 'SF Pro Display', 'SF Pro Text', 
             'SF Pro Icons', 'Helvetica Neue', 
             'Helvetica', 'Arial', sans-serif;
```

**光学尺寸:**
- SF Pro Display: 20px+
- SF Pro Text: <20px

**负字母间距:**
- 56px: -0.28px
- 17px: -0.374px
- 14px: -0.224px
- 12px: -0.12px

### 3. 圆角系统

**Decision:** 采用 DESIGN.md 定义的圆角

**Values:**
- Micro (5px): 小容器、链接标签
- Standard (8px): 按钮、产品卡片
- Comfortable (11px): 搜索框、筛选按钮
- Large (12px): 功能面板、生活方式图片
- Full Pill (980px): CTA 链接（"Learn more"、"Shop"）
- Circle (50%): 媒体控制按钮

### 4. 阴影系统

**Decision:** 采用单一的柔和阴影

**Apple 风格阴影:**
```css
box-shadow: rgba(0, 0, 0, 0.22) 3px 5px 30px 0px;
```

**Rationale:**
Apple 极少使用阴影，只用这一个柔和、扩散的阴影来模拟摄影棚灯光下的自然阴影。

### 5. 导航栏设计

**Decision:** 采用 Apple 风格的半透明玻璃导航

**设计要点:**
- 背景：`rgba(0, 0, 0, 0.8)`
- 模糊效果：`backdrop-filter: saturate(180%) blur(20px)`
- 高度：48px
- 文字：12px, weight 400, 白色

**Rationale:**
这是 Apple 网站最具辨识度的设计元素之一。

### 6. 按钮设计

**Decision:** 采用 DESIGN.md 定义的按钮样式

**Primary Blue:**
- 背景：#0071e3
- 文字：#ffffff
- 内边距：8px 15px
- 圆角：8px

**Pill Link (Learn More):**
- 背景：透明
- 文字：#0066cc (浅背景) 或 #2997ff (深背景)
- 圆角：980px（完整胶囊形）
- 边框：1px solid #0066cc

## Risks / Trade-offs

### [Risk 1] 视觉风格主观性

**Risk:** Apple 风格是主观的，可能不完全符合用户期望

**Mitigation:** 
- 参考多个 Apple 产品页面（apple.com, iCloud, Apple Support）
- 保持设计一致性而非完美复制

### [Risk 2] 浏览器兼容性

**Risk:** backdrop-filter 等 CSS 特性在旧浏览器不支持

**Mitigation:**
- 提供降级样式
- 使用渐进增强

### [Risk 3] 样式覆盖不完整

**Risk:** 某些页面可能遗漏样式更新

**Mitigation:**
- 系统性地重构所有模板
- 部署前全面测试所有页面

## Migration Plan

### Phase 1: 设计令牌
1. 定义新的 CSS 变量（颜色、字体、间距、圆角、阴影）
2. 保持旧变量向后兼容

### Phase 2: 组件重构
1. 重构按钮、表单、卡片组件
2. 重构导航栏
3. 重构排版系统

### Phase 3: 页面应用
1. 更新 base.html
2. 逐一更新所有模板页面

### Phase 4: 测试与优化
1. 测试所有页面和功能
2. 优化动画性能
3. 测试响应式设计

**Rollback Strategy:**
- 保留旧版 CSS 文件作为备份
- 如发现问题可快速切换回旧样式

## Open Questions

1. 是否需要引入深色模式支持？
2. 是否需要自定义图标替代 Font Awesome？
3. 是否需要添加动画偏好设置（减少动画）？
