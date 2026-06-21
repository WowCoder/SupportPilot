## ADDED Requirements

### Requirement: FAQ 管理页面布局
FAQ 管理 SPA 页面 SHALL 使用 Element Plus 组件，顶部显示统计卡片（`el-row` + `el-col` 4 卡片），下方 `el-table` 展示 FAQ 列表，支持筛选、分页、批量操作。

#### Scenario: 页面结构
- **WHEN** 技术支持人员访问 `/faq` 路由
- **THEN** 页面 MUST 显示 "FAQ 管理" 标题
- **THEN** MUST 显示 4 个统计卡片（总数/已确认/待审核/草稿），从 API 实时加载

### Requirement: Element Plus 数据表格
FAQ 列表 SHALL 使用 `el-table` 组件，列包括：选择框（`el-table-column type="selection"`）、问题、答案预览（截断 100 字符）、分类、状态（`el-tag` 颜色区分）、创建时间、操作按钮。

#### Scenario: 表格渲染
- **WHEN** FAQ 数据从 API 加载完成
- **THEN** `el-table` MUST 显示每行的问题、答案预览、分类、状态 tag（confirmed 绿色/pending 黄色/draft 灰色/rejected 红色）、创建时间
- **THEN** 每行操作列 MUST 包含编辑、版本历史、删除按钮

#### Scenario: 空数据
- **WHEN** API 返回空列表
- **THEN** `el-table` empty slot MUST 显示 "暂无 FAQ" 空状态

### Requirement: 筛选栏
表格上方 SHALL 包含筛选栏：状态下拉（`el-select`）、分类下拉、搜索输入框（`el-input`），筛选条件变化时自动重新加载表格。

#### Scenario: 状态筛选
- **WHEN** 用户更改状态下拉选择
- **THEN** 表格 MUST 重新调用 API 并加载对应状态的 FAQ

#### Scenario: 搜索
- **WHEN** 用户输入搜索关键词并回车（或 @input 防抖 300ms）
- **THEN** 表格 MUST 重新调用 API 并传递 `search` 参数

### Requirement: 分页
表格下方 SHALL 使用 `el-pagination` 组件，支持修改每页条数和跳转页码。

#### Scenario: 分页交互
- **WHEN** 用户点击下一页或更改每页条数
- **THEN** `el-pagination` MUST 触发 API 重新加载对应页数据
- **THEN** 当前页码和总条数 MUST 更新

### Requirement: 批量操作
`el-table` 首列 `type="selection"` SHALL 支持全选/多选，当选中行数 > 0 时显示批量操作栏（选中计数 + 批量删除按钮）。

#### Scenario: 全选和批量删除
- **WHEN** 用户勾选表头 checkbox
- **THEN** 所有可见行 MUST 被选中
- **THEN** 批量操作栏 MUST 显示选中计数
- **WHEN** 用户点击 "批量删除" 并确认
- **THEN** MUST 调用批量删除 API 并刷新列表

### Requirement: 新增/编辑 FAQ Modal
点击 "新增 FAQ" 或 "编辑" 按钮 SHALL 打开 `el-dialog`，包含 `el-form`（问题 textarea、答案 textarea、分类 input、修改原因 input）。

#### Scenario: 新增 FAQ
- **WHEN** 用户点击 "新增 FAQ"
- **THEN** `el-dialog` 标题 MUST 为 "新增 FAQ"
- **THEN** 表单 MUST 为空
- **THEN** 保存后 MUST POST `/api/v1/faq/entries`

#### Scenario: 编辑 FAQ
- **WHEN** 用户点击某行的 "编辑"
- **THEN** `el-dialog` 标题 MUST 为 "编辑 FAQ"
- **THEN** 表单 MUST 回填现有数据
- **THEN** 编辑已确认/草稿 FAQ 时 MUST 显示 "修改原因" 字段和 "保存" 按钮
- **THEN** 编辑待审核 FAQ 时 MUST 显示 "确认并添加" 按钮（触发向量同步）

### Requirement: 向量同步进度
确认待审核 FAQ 时 SHALL 在 Modal 内显示 `el-progress` 进度条和状态文字。

#### Scenario: 向量同步
- **WHEN** 用户点击 "确认并添加"
- **THEN** Modal 内 MUST 显示 `el-progress` 组件和 "正在向量化..." 文字
- **THEN** 完成后 MUST 显示 "向量化完成" 并关闭 Modal

### Requirement: 版本历史 Modal
点击 "版本历史" SHALL 打开 `el-dialog`，使用 `el-timeline` 展示该 FAQ 的历史版本。

#### Scenario: 版本历史展示
- **WHEN** 用户点击 "版本历史"
- **THEN** `el-dialog` MUST 包含 `el-timeline`，每个节点显示版本时间、修改原因、问题内容、答案内容

### Requirement: 删除确认
删除操作 SHALL 使用 `el-message-box` 确认对话框，显示警告信息和提示文字。

#### Scenario: 删除确认
- **WHEN** 用户点击删除按钮
- **THEN** `el-message-box.confirm` MUST 弹出显示 exclamation-triangle 图标和 "此操作将同时从知识库中移除相关条目" 提示
- **THEN** 确认后 MUST 调用删除 API
