## ADDED Requirements

### Requirement: FAQ 管理页面布局
FAQ 管理页面 SHALL 使用 topnav + page-content 布局，包含统计卡片（总 FAQ 数/已确认/待审核/草稿）、filter-bar（状态筛选 + 分类筛选 + 搜索）、数据表格（含 checkbox 全选/分页）、批量操作栏、3 个 Modal（新增/编辑 + 版本历史 + 删除确认）。

#### Scenario: 页面结构
- **WHEN** 技术支持人员访问 FAQ 管理页面
- **THEN** 页面 MUST 显示 "FAQ 管理" 标题
- **THEN** 页面 MUST 显示 4 个统计卡片（总 FAQ 数、已确认、待审核、草稿）

### Requirement: 统计卡片
页面顶部 SHALL 显示 4 个统计卡片（total/confirmed/pending/draft），数据通过 AJAX 加载。

#### Scenario: 统计卡片数据加载
- **WHEN** FAQ 管理页面加载
- **THEN** 统计卡片 MUST 从 `/api/faq` 获取并展示最新统计数据
- **THEN** 卡片数值 MUST 随筛选条件同步更新

### Requirement: Filter Bar 筛选栏
Filter bar SHALL 包含三个筛选控件：状态下拉（全部/已确认/待审核/草稿/已拒绝）、分类下拉（动态加载分类列表）、搜索输入框（支持回车搜索）。

#### Scenario: 状态筛选
- **WHEN** 用户选择不同的状态（如 "待审核"）
- **THEN** 表格 MUST 重新加载并只显示该状态的 FAQ

#### Scenario: 分类筛选
- **WHEN** 用户选择分类
- **THEN** 表格 MUST 重新加载并只显示该分类的 FAQ

#### Scenario: 搜索过滤
- **WHEN** 用户输入搜索关键词并回车（或点击搜索按钮）
- **THEN** 系统 MUST 调用 `/api/faq?search=<keyword>` 并更新表格

### Requirement: FAQ 数据表格
FAQ 列表 SHALL 以 `.data-table` 表格形式展示，列包括：checkbox（全选/单选）、问题、答案预览（截断 100 字符）、分类、状态 badge（颜色区分）、创建时间、操作按钮（编辑/版本历史/删除）。

#### Scenario: 表格渲染
- **WHEN** FAQ 数据加载完成
- **THEN** 每行 MUST 显示问题、答案预览（100 字符后加 "..."）、分类、状态 badge、创建时间
- **THEN** 状态 badge MUST 按状态显示不同颜色：confirmed（绿）、pending_review（黄）、draft（灰）、rejected（红）

#### Scenario: 行操作按钮
- **WHEN** 鼠标悬停在某行
- **THEN** MUST 显示三个操作按钮：编辑（secondary）、版本历史（info）、删除（danger）

#### Scenario: 空数据
- **WHEN** 筛选结果为空
- **THEN** MUST 显示 "暂无 FAQ" 空状态

### Requirement: 分页
表格下方 SHALL 显示分页导航（上一页/下一页 + 当前页码/总页数），每页 20 条。

#### Scenario: 分页导航
- **WHEN** FAQ 总数超过 20 条
- **THEN** MUST 显示分页控件
- **WHEN** 在第一页
- **THEN** "上一页" 按钮 MUST 不可用
- **WHEN** 在最后一页
- **THEN** "下一页" 按钮 MUST 不可用

### Requirement: 全选和批量操作栏
表头 checkbox SHALL 支持全选/取消全选，当至少 1 行被选中时显示 bulk-bar（已选计数 + 批量删除按钮）。

#### Scenario: 全选
- **WHEN** 用户勾选表头 checkbox
- **THEN** 所有行 checkbox MUST 被选中
- **THEN** bulk-bar MUST 显示选中计数
- **WHEN** 用户取消表头 checkbox
- **THEN** 所有行 checkbox MUST 取消
- **THEN** bulk-bar MUST 隐藏

#### Scenario: 批量删除
- **WHEN** 用户点击 "批量删除" 并确认
- **THEN** MUST 调用 `/api/faq/bulk-delete`（POST）
- **THEN** 成功后 MUST 刷新列表和统计

### Requirement: 新增/编辑 FAQ Modal
点击 "新增 FAQ" 或 "编辑" 按钮 SHALL 打开 modal，包含问题（textarea）、答案（textarea）、分类（input）、修改原因（input，编辑时显示）字段、保存/取消按钮。

#### Scenario: 新增 FAQ
- **WHEN** 用户点击 "新增 FAQ"
- **THEN** Modal 标题 MUST 为 "新增 FAQ"
- **THEN** 表单 MUST 为空
- **THEN** 修改原因字段 MUST 隐藏
- **THEN** 确认按钮 MUST 隐藏

#### Scenario: 编辑 FAQ（已确认/草稿状态）
- **WHEN** 用户编辑已确认或草稿的 FAQ
- **THEN** Modal 标题 MUST 为 "编辑 FAQ"
- **THEN** 表单 MUST 回填现有数据
- **THEN** 修改原因字段 MUST 显示
- **THEN** 显示 "保存" 按钮

#### Scenario: 编辑 FAQ（待审核状态）
- **WHEN** 用户编辑待审核的 FAQ
- **THEN** 表单 MUST 回填现有数据
- **THEN** "保存" 按钮 MUST 隐藏
- **THEN** MUST 显示 "确认并添加" 按钮（确认后同步到向量库）

#### Scenario: 保存 FAQ
- **WHEN** 用户点击 "保存"
- **THEN** 新增 MUST POST `/api/faq`，编辑 MUST PUT `/api/faq/<id>`
- **THEN** 成功后 MUST 关闭 modal 并刷新列表

### Requirement: 向量同步进度
待审核 FAQ 确认时 SHALL 在 modal 内显示向量化进度条和状态文字。

#### Scenario: 向量同步进度展示
- **WHEN** 用户点击 "确认并添加"
- **THEN** Modal 内 MUST 显示进度条和 "正在向量化..." 文字
- **THEN** 进度 MUST 从 0% 更新至 100%
- **THEN** 成功后 MUST 显示 "向量化完成"

### Requirement: 版本历史 Modal
点击 "版本历史" SHALL 打开 modal，显示该 FAQ 的所有历史版本，每条包含修改时间、修改原因、问题内容、答案内容。

#### Scenario: 版本历史展示
- **WHEN** 用户点击版本的 "版本历史" 按钮
- **THEN** MUST 调用 `/api/faq/<id>/versions` 并展示列表
- **THEN** 每条版本 MUST 显示时间（含 clock 图标）、修改原因、问题原文、答案原文

### Requirement: 删除确认 Modal
点击删除按钮（单个或批量）SHALL 打开删除确认 modal，显示警告图标和"此操作将同时从知识库中移除相关条目"提示。

#### Scenario: 删除确认
- **WHEN** 用户点击删除
- **THEN** Modal MUST 显示 exclamation-triangle 图标
- **THEN** Modal MUST 显示提示文字 "此操作将同时从知识库中移除相关条目"
- **THEN** 确认后 MUST POST `/api/faq/bulk-delete`

### Requirement: Modal 交互
所有 Modal SHALL 支持点击遮罩层关闭和 ESC 键关闭。

#### Scenario: ESC 关闭
- **WHEN** 用户按下 ESC 键
- **THEN** 当前打开的 modal MUST 关闭

#### Scenario: 遮罩层关闭
- **WHEN** 用户点击 modal 外部遮罩区域
- **THEN** modal MUST 关闭

### Requirement: 原型功能差异 — 原型缺失的现有功能
以下现有功能在设计原型中未体现（原型使用手风琴列表），实现时 MUST 保留：
- 4 个统计卡片（总 FAQ 数/已确认/待审核/草稿）及动态更新
- 状态筛选下拉（全部/已确认/待审核/草稿/已拒绝）+ 分类筛选下拉 + 搜索输入框
- **数据表格布局**（非手风琴列表）保留 checkbox 全选、行操作按钮
- 分页导航
- 3 个 Modal：FAQ 表单 Modal（含保存/确认双向流程）、版本历史 Modal、删除确认 Modal
- 向量同步进度条（确认待审核 FAQ 时）
- 修改原因字段（编辑 FAQ 时）
- 编辑时区分已确认/待审核的确认+向量化流程

### Requirement: 原型功能差异 — 原型有但当前不存在
以下原型功能当前不存在，暂不保留：
- 手风琴列表布局 — 保持当前表格布局
- 原型中的 category filter-tabs（分段控件）— 保持当前下拉选择器
- 原型中的 Export 按钮 — 后端无导出 API
