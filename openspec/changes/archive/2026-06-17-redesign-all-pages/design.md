## Context

当前项目使用 Flask + Jinja2 模板渲染，CSS 为自定义旧样式（`static/css/style.css`），各页面风格不统一。已有完整的设计原型位于 `设计原型/整体页面重新设计-2026_5_26/`，包含新的 CSS 设计系统和 7 个页面的 HTML 原型。

## Goals / Non-Goals

**Goals:**
- 将所有 8 个模板文件重构为统一 Apple-style 设计系统
- 用 CSS 变量驱动全部样式，消灭硬编码颜色值
- 保持现有 Jinja2/Flask 模板逻辑和数据绑定不变
- 新 UI 组件（badge, toast, modal, toggle, filter-tabs）在模板中可用
- 移动端响应式支持

**Non-Goals:**
- 不修改后端路由、API、服务层代码
- 不改变页面 URL 结构
- 不添加新的 JS 库/框架依赖
- 不改变现有 Flask-Login 认证流程

## Decisions

### 1. 纯 CSS 方案，不引入 JS 框架
**选择**: 保持原生 HTML + CSS + 少量 vanilla JS
**原因**: 项目是 Flask 传统 SSR 架构，引入 React/Vue 成本过高。设计原型已证明纯 CSS 可实现目标效果。避免增加构建工具链。

### 2. CSS 完全替换而非增量修改
**选择**: 用新的 `style.css` 完全替换旧 CSS
**原因**: 旧 CSS 类名和变量体系与新设计不兼容，增量修改会产生大量死代码。一次性替换更干净。

### 3. 模板结构以设计原型为蓝本
**选择**: 模板 HTML 结构严格对齐 `设计原型/整体页面重新设计-2026_5_26/*.html`
**原因**: 原型已经过视觉验证，保持结构一致确保最终效果与原型一致。

### 4. JS 逻辑内联于模板
**选择**: 将交互 JS（filter-tabs, accordion, toast 等）内联在模板 `{% block extra_js %}` 中
**原因**: 项目无前端构建工具，内联 JS 避免额外依赖。代码量小（每个页面 ~30 行），不会造成维护负担。

### 5. 保留 Jinja2 动态部分
**选择**: 原型中的静态 mock 数据替换为 Jinja2 模板语法和循环
**原因**: 保持与后端数据模型的绑定。如 `{{ conversations|length }}`、`{% for item in items %}` 等保持不变。

## Risks / Trade-offs

- **CSS 变量兼容性**: 依赖 CSS 自定义属性，IE 不支持。但目标用户均为现代浏览器，风险可接受。
- **一次性替换风险**: 全量替换如果出现问题，回退需要 git revert。通过保留旧 CSS 文件备份来缓解。
- **JS 内联维护**: 每个页面有少量内联 JS，未来可能重复。当前项目规模小（~8 个页面），可接受。如果扩展到 20+ 页面，再考虑提取公共 JS 文件。
- **设计原型与后端数据不匹配**: 原型使用 mock 数据，实际集成时可能发现缺少某些 UI 状态（如 loading、error）。实现时需补充。

## Migration Plan

1. 备份 `static/css/style.css`（重命名为 `style-old.css`）
2. 写入新的 `style.css`（从设计原型复制）
3. 逐个模板重写，从 base.html 开始（导航基础设施）
4. 每完成一个模板，浏览器验证视觉效果
5. 全部完成后，删除旧 CSS 备份

## Open Questions

- 无
