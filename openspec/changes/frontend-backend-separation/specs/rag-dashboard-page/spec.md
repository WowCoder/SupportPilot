## MODIFIED Requirements

### Requirement: Dashboard 页面入口
仅技术支持角色 SHALL 能访问 `/rag-dashboard` 路由（Vue Router），普通用户访问 SHALL 由导航守卫重定向回首页。

#### Scenario: 权限控制
- **WHEN** 普通用户尝试访问 `/rag-dashboard`
- **THEN** Vue Router 导航守卫 MUST 重定向到首页
- **THEN** MUST 显示 `el-message.warning` "权限不足"

### Requirement: Dashboard 整体布局
Dashboard SHALL 使用 Vue 组件实现：顶部 `el-row` + `el-col` 统计卡片区（4 卡片），下方 `el-table` 检索日志列表。

#### Scenario: 统计卡片
- **WHEN** 技术支持访问 Dashboard
- **THEN** MUST 显示 4 个 `el-card`（或带统计数字的卡片）：
  - 总检索次数（当日/总计）
  - 正反馈率（👍 / 总反馈 百分比）
  - 平均 Top-1 相似度
  - LLM-Judge 均分
- **THEN** 卡片数值 MUST 从 `/api/v1/rag/dashboard` 加载，加载中使用 `v-loading`

### Requirement: 检索日志列表
Dashboard 主体 SHALL 使用 `el-table` 展示检索日志，支持行展开和筛选。

#### Scenario: 日志列表展开详情
- **WHEN** 技术支持点击某条日志行
- **THEN** `el-table` expand row MUST 显示原始查询全文、路由方式、每条检索结果的完整内容+相似度+来源文件、LLM-Judge 三维评分

#### Scenario: 日志列表筛选
- **WHEN** 技术支持使用筛选器
- **THEN** 筛选器 MUST 使用 `el-select`（路由方式）和 `el-input`（搜索关键词）
- **THEN** 表格 MUST 重新加载过滤数据

### Requirement: 低质量查询高亮
Dashboard SHALL 通过 `el-table` 的 `row-class-name` 属性高亮低质量检索记录。

#### Scenario: 低质量标记
- **WHEN** top-1 相似度 < 0.3 或 judge 均分 < 3
- **THEN** 该行 MUST 添加红色左边框样式（通过 `row-class-name` 返回的 CSS class）
