## ADDED Requirements

### Requirement: Upload SPA 页面布局
文档上传 SPA 页面 SHALL 显示标题 "上传知识库文档"、统计卡片（文档数和片段数）、上传向导、检索测试区、已上传文档列表。

#### Scenario: 页面结构
- **WHEN** 技术支持人员访问 `/upload` 路由
- **THEN** 页面 MUST 显示统计卡片（已上传文档数、知识库片段数）
- **THEN** 页面主体 MUST 显示上传向导

### Requirement: 四步骤上传向导
上传流程 SHALL 使用 `el-steps` 步骤条组件，包含 4 个步骤：选择文档 → 数据清洗 → 分块设置 → 完成上传。支持前进/后退。

#### Scenario: 步骤指示器
- **WHEN** 页面加载
- **THEN** `el-steps` MUST 显示 4 个步骤，当前步骤高亮（`active`），已完成步骤显示对勾
- **THEN** "上一步"/"下一步" 按钮 MUST 切换步骤面板

### Requirement: Step 1 — 文件选择
第一步 SHALL 使用 `el-upload` 组件实现拖拽上传区，支持 PDF/TXT/DOC/DOCX 格式，最大 16MB。

#### Scenario: 拖拽上传
- **WHEN** 用户拖拽文件到上传区
- **THEN** `el-upload` drag 区域 MUST 高亮
- **THEN** 文件释放后 MUST 显示文件信息卡（文件名、大小）
- **THEN** "下一步" 按钮 MUST 变为可用

#### Scenario: 格式限制
- **WHEN** 用户选择不支持的文件格式
- **THEN** `el-upload` `before-upload` hook MUST 阻止上传并显示 `el-message.error`

### Requirement: Step 2 — 数据清洗
第二步 SHALL 包含 6 个清洗选项（`el-checkbox-group`）、预览清洗按钮、清洗前后对比展示。

#### Scenario: 清洗选项
- **WHEN** Step 2 加载
- **THEN** MUST 显示 6 个 checkbox（全部默认选中）：移除页眉页脚、移除页码、清理噪音字符、规范化空白、OCR 后处理、过滤非正文

#### Scenario: 清洗预览
- **WHEN** 用户点击 "预览清洗效果"
- **THEN** MUST 调用后端 API 并展示对比：原始字符数、清洗后字符数、缩减百分比
- **THEN** MUST 显示左右对比面板（原始 vs 清洗后文本，各展示前 3000 字符）

### Requirement: Step 3 — 分块设置
第三步 SHALL 包含 3 种分块策略的 `el-radio-group` 选择、对应参数输入、Small-to-Big toggle、分块预览。

#### Scenario: 策略选择
- **WHEN** Step 3 加载
- **THEN** MUST 显示 3 个 `el-radio` 卡片：句子分块（推荐）、语义分块、递归分块
- **THEN** 选择不同策略 MUST 切换对应参数面板

#### Scenario: Small-to-Big 配置
- **WHEN** "启用 Small-to-Big" toggle 开启（默认）
- **THEN** MUST 显示大块大小和小块大小输入框

#### Scenario: 分块预览
- **WHEN** 用户点击 "预览分块效果"
- **THEN** MUST 调用后端 API 并展示统计（总块数、总字符数、平均大小）

### Requirement: Step 4 — 确认与上传
第四步 SHALL 显示所有配置摘要（文档信息、清洗结果、分块设置）和上传进度。

#### Scenario: 上传进度
- **WHEN** 用户点击 "开始上传"
- **THEN** MUST 显示 `el-progress` 进度条（百分比 + 状态文字："正在上传..." → "正在处理..." → "上传成功!"）
- **THEN** 成功页 MUST 显示绿色成功图标、"上传成功！" 文字、知识库片段数、"继续上传" 和 "检索测试" 按钮

### Requirement: RAG 检索测试区
页面底部 SHALL 包含检索测试区，使用 Element Plus 表单组件，展示带相似度分数的检索结果。

#### Scenario: 检索测试
- **WHEN** 用户在检索测试区输入查询并点击 "开始检索"
- **THEN** MUST 调用 API 并展示结果列表（每行含来源文件名、相似度百分比 + 颜色区分、内容文本）

### Requirement: 已上传文档列表
页面底部 SHALL 使用 Element Plus 组件展示文档列表，支持分页和删除。

#### Scenario: 文档列表与删除
- **WHEN** 有已上传文档
- **THEN** 每行 MUST 显示文件图标（按格式区分颜色）、文件名、上传时间、删除按钮
- **THEN** 删除 MUST 弹出 `el-message-box.confirm` 确认
