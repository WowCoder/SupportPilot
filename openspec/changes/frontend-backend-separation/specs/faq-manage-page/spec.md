## MODIFIED Requirements

### Requirement: FAQ 管理页面布局
FAQ 管理页面 SHALL 使用 Vue 组件实现：顶部统计卡片（Element Plus `el-row` + `el-col` 4 卡片），下方 `el-table` 展示 FAQ 列表。

#### Scenario: 页面结构
- **WHEN** 技术支持人员访问 `/faq` 路由
- **THEN** 页面 MUST 显示 "FAQ 管理" 标题
- **THEN** MUST 显示 4 个统计卡片（总 FAQ 数/已确认/待审核/草稿），数据通过 Axios 加载

### Requirement: 统计卡片
页面顶部 SHALL 显示 4 个统计卡片，数据通过 Pinia store 管理，从 API 异步加载。

#### Scenario: 统计卡片数据加载
- **WHEN** FAQ 管理页面 mounted
- **THEN** 统计卡片 MUST 从 `/api/v1/faq/entries?stats=true`（或等效端点）获取数据
- **THEN** 卡片数值 MUST 随筛选条件变化同步更新

### Requirement: Filter Bar 筛选栏
Filter bar SHALL 使用 Element Plus 组件：`el-select`（状态筛选）、`el-select`（分类筛选）、`el-input`（搜索，支持防抖 300ms）。

#### Scenario: 状态筛选
- **WHEN** 用户选择不同的状态
- **THEN** `el-table` MUST 重新调用 API 并加载对应状态的 FAQ

#### Scenario: 搜索过滤
- **WHEN** 用户输入搜索关键词（300ms 防抖后）
- **THEN** MUST 调用 API 并传递 `search` 参数

### Requirement: FAQ 数据表格
FAQ 列表 SHALL 使用 `el-table`，列包括：`type="selection"` checkbox、问题、答案预览（截断 100 字符）、分类、状态（`el-tag` 颜色区分）、创建时间、操作按钮。

#### Scenario: 表格渲染
- **WHEN** FAQ 数据加载完成
- **THEN** `el-table` 每行 MUST 显示问题、答案预览（截断 100 字符 + "..."）、分类、状态 `el-tag`（confirmed 绿色/pending 黄色/draft 灰色/rejected 红色）、创建时间
- **THEN** 操作列 MUST 包含编辑、版本历史、删除 `el-button`

#### Scenario: 空数据
- **WHEN** API 返回空列表
- **THEN** `el-table` empty slot MUST 显示 "暂无 FAQ"

### Requirement: 分页
表格下方 SHALL 使用 `el-pagination` 组件，每页 20 条。

#### Scenario: 分页导航
- **WHEN** FAQ 总数超过 20 条
- **THEN** `el-pagination` MUST 显示，支持切换页码和每页条数
- **THEN** 变更时 MUST 触发 API 重新加载

### Requirement: 全选和批量操作栏
`el-table` `type="selection"` SHALL 支持全选/多选，选中时显示批量操作栏（`el-alert` 或自定义 bar，含选中计数 + 批量删除 `el-button`）。

#### Scenario: 全选
- **WHEN** 用户勾选表头 checkbox
- **THEN** 所有可见行 MUST 被选中
- **THEN** 批量操作栏 MUST 显示选中计数

#### Scenario: 批量删除
- **WHEN** 用户点击 "批量删除" 并确认
- **THEN** MUST 调用 `/api/v1/faq/entries/bulk-delete`（POST）
- **THEN** 成功后 MUST 刷新列表和统计

### Requirement: 新增/编辑 FAQ Modal
点击 "新增 FAQ" 或编辑按钮 SHALL 打开 `el-dialog`，包含 `el-form`（问题 textarea、答案 textarea、分类 input、修改原因 input）。

#### Scenario: 新增 FAQ
- **WHEN** 用户点击 "新增 FAQ"
- **THEN** `el-dialog` 标题 MUST 为 "新增 FAQ"
- **THEN** 表单 MUST 为空，修改原因字段 MUST 隐藏
- **THEN** 保存 MUST POST `/api/v1/faq/entries`

#### Scenario: 编辑 FAQ（已确认/草稿）
- **WHEN** 用户编辑已确认或草稿 FAQ
- **THEN** `el-dialog` 标题 MUST 为 "编辑 FAQ"
- **THEN** 表单 MUST 回填现有数据，修改原因字段 MUST 显示
- **THEN** "保存" 按钮 MUST 可见

#### Scenario: 编辑 FAQ（待审核）
- **WHEN** 用户编辑待审核 FAQ
- **THEN** "保存" 按钮 MUST 隐藏
- **THEN** "确认并添加" 按钮 MUST 显示（确认后触发向量同步）

### Requirement: 向量同步进度
待审核 FAQ 确认时 SHALL 在 `el-dialog` 内显示 `el-progress` 组件。

#### Scenario: 向量同步进度展示
- **WHEN** 用户点击 "确认并添加"
- **THEN** `el-dialog` 内 MUST 显示 `el-progress` + "正在向量化..." 文字
- **THEN** 进度 MUST 从 0% 更新至 100%
- **THEN** 完成后 MUST 显示 "向量化完成" 并关闭 Modal

### Requirement: 版本历史 Modal
点击 "版本历史" SHALL 打开 `el-dialog`，使用 `el-timeline` 展示版本历史。

#### Scenario: 版本历史展示
- **WHEN** 用户点击 "版本历史"
- **THEN** MUST 调用 API 获取版本历史
- **THEN** `el-timeline` 每条记录 MUST 显示时间、修改原因、问题原文、答案原文

### Requirement: 删除确认 Modal
删除操作 SHALL 使用 `el-message-box.confirm`。

#### Scenario: 删除确认
- **WHEN** 用户点击删除按钮
- **THEN** `el-message-box.confirm` MUST 弹出，显示警告图标和提示文字
- **THEN** 确认后 MUST 调用删除 API

### Requirement: Modal 交互
所有 `el-dialog` SHALL 支持点击遮罩层关闭（`close-on-click-modal`）和 ESC 键关闭（`close-on-press-escape`）。

#### Scenario: ESC 关闭
- **WHEN** 用户按下 ESC 键
- **THEN** 当前打开的 `el-dialog` MUST 关闭

## REMOVED Requirements

### Requirement: 原型功能差异 — 原型缺失的现有功能
**Reason**: 前端完全重写为 Vue 组件，`.data-table`、CSS class 等被 Element Plus 组件替代
**Migration**: 所有 CSS class 映射到 Element Plus 组件属性；表格、模态框、分页等使用对应 el-* 组件

### Requirement: 原型功能差异 — 原型有但当前不存在
**Reason**: Vue 重写以现有功能为基准
**Migration**: Export 等未实现功能在后续迭代通过 Element Plus 组件添加
