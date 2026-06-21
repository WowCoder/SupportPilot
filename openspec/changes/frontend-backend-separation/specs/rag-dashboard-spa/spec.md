## ADDED Requirements

### Requirement: Dashboard 权限控制
仅技术支持角色 SHALL 能访问 `/rag-dashboard` 路由，普通用户访问时 MUST 重定向到首页。

#### Scenario: 权限守卫
- **WHEN** 普通用户尝试访问 `/rag-dashboard`
- **THEN** Vue Router 导航守卫 MUST 重定向到首页并显示 `el-message.warning` "权限不足"

### Requirement: 统计卡片区
Dashboard 顶部 SHALL 使用 `el-row` + `el-col` 显示 4 个统计卡片：总检索次数、正反馈率、平均 Top-1 相似度、LLM-Judge 均分。数据通过 Pinia actions 异步加载。

#### Scenario: 统计卡片加载
- **WHEN** Dashboard 组件 mounted
- **THEN** MUST 调用 `GET /api/v1/rag/dashboard` 加载统计数据
- **THEN** 4 个 `el-card` MUST 展示最新数值，加载中使用 `v-loading` 显示骨架

### Requirement: 检索日志表格
Dashboard 主体 SHALL 使用 `el-table` 展示检索日志，每行显示查询、结果数、Top-1 相似度（颜色区分）、Judge 评分、耗时、时间。支持筛选和搜索。

#### Scenario: 日志列表渲染
- **WHEN** 日志数据加载完成
- **THEN** `el-table` MUST 显示每行的查询、结果数、相似度（>=0.7 绿色 tag，0.4-0.7 橙色，<0.4 红色）、Judge 评分、耗时、时间

#### Scenario: 筛选
- **WHEN** 技术支持使用筛选器选择路由方式（agentic/simple）或输入搜索关键词
- **THEN** 表格 MUST 重新加载过滤后的数据

#### Scenario: 展开详情
- **WHEN** 技术支持点击某行
- **THEN** `el-table` expand row MUST 显示原始查询全文、路由方式、每条检索结果的完整内容+相似度+来源文件、LLM-Judge 三维评分

### Requirement: 低质量查询高亮
Top-1 相似度 < 0.3 或 Judge 均分 < 3 的记录 SHALL 在表格中高亮标记。

#### Scenario: 低质量行标记
- **WHEN** top-1 相似度 < 0.3 或 judge 均分 < 3
- **THEN** 该行 `row-class-name` MUST 添加红色左边框样式
