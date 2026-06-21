## MODIFIED Requirements

### Requirement: Upload 页面布局
文档上传页面 SHALL 使用 Vue 组件实现：统计卡片（`el-row` + `el-col`）、上传向导、检索测试区、已上传文档列表。

#### Scenario: 页面整体结构
- **WHEN** 技术支持人员访问 `/upload` 路由
- **THEN** 页面 MUST 显示标题 "上传知识库文档"
- **THEN** MUST 包含统计卡片区（已上传文档数、知识库片段数）

### Requirement: 四步骤上传向导
上传流程 SHALL 使用 `el-steps` 步骤条，包含 4 个步骤：选择文档 → 数据清洗 → 分块设置 → 完成上传。通过 Vue 响应式变量控制步骤切换。

#### Scenario: 步骤指示器展示
- **WHEN** 页面加载
- **THEN** `el-steps` MUST 显示 4 个步骤，当前步骤 `active`，已完成步骤显示对勾
- **THEN** 步骤间连线 MUST 显示进度

#### Scenario: 步骤导航
- **WHEN** 用户点击 "下一步" 按钮
- **THEN** 当前步骤 `activeStep` 变量 MUST +1，步骤指示器同步更新
- **WHEN** 用户点击 "上一步" 按钮
- **THEN** 当前步骤变量 MUST -1，已填写数据通过 Vue 响应式保留

### Requirement: Step 1 — 选择文档
第一步 SHALL 使用 `el-upload` 的 drag 模式实现拖拽上传区，支持 PDF/TXT/DOC/DOCX 格式，最大 16MB。

#### Scenario: 拖拽上传
- **WHEN** 用户拖拽文件到 `el-upload` drag 区域
- **THEN** 区域 MUST 显示 drag-over 样式（Element Plus 内置）
- **WHEN** 文件释放
- **THEN** 文件信息卡 MUST 显示（文件名、大小）
- **THEN** "下一步" 按钮 MUST 变为可用

#### Scenario: 清除文件
- **WHEN** 用户点击清除按钮
- **THEN** 文件列表 MUST 清空
- **THEN** "下一步" 按钮 MUST 变为 disabled

#### Scenario: 文件格式限制
- **WHEN** 用户选择不支持的文件格式
- **THEN** `el-upload` `before-upload` hook MUST 阻止并显示 `el-message.error`

### Requirement: Step 2 — 数据清洗
第二步 SHALL 使用 `el-checkbox-group` 包含 6 个清洗选项、预览清洗按钮、清洗对比面板、元数据编辑 `el-form`。

#### Scenario: 清洗选项
- **WHEN** Step 2 加载
- **THEN** MUST 显示 6 个 `el-checkbox`（全部默认选中）：移除页眉页脚、移除页码、清理噪音字符、规范化空白、OCR 后处理、过滤非正文

#### Scenario: 预览清洗效果
- **WHEN** 用户点击 "预览清洗效果" 按钮
- **THEN** MUST 调用 API 并展示对比结果（原始字符数、清洗后字符数、缩减百分比）
- **THEN** MUST 显示左右对比面板（原始 vs 清洗后，各展示前 3000 字符）

#### Scenario: 跳过清洗
- **WHEN** 用户点击 "跳过清洗" 按钮
- **THEN** MUST 直接跳到 Step 3，不传递清洗参数

### Requirement: Step 3 — 分块设置
第三步 SHALL 使用 `el-radio-group` 展示 3 种分块策略卡片、对应参数输入、Small-to-Big `el-switch`、分块预览。

#### Scenario: 策略选择卡片
- **WHEN** Step 3 加载
- **THEN** MUST 显示 3 个策略卡片（`el-radio` 选择）：
  - 句子分块（推荐）：按句子边界分块
  - 语义分块：基于 embedding 相似度
  - 递归分块：按固定字符数切分

#### Scenario: 策略切换联动
- **WHEN** 用户选择不同策略
- **THEN** 对应的参数输入框 MUST 动态切换显示

#### Scenario: Small-to-Big 配置
- **WHEN** Small-to-Big `el-switch` 开启（默认）
- **THEN** MUST 显示大块大小和小块大小 `el-input-number`

#### Scenario: 预览分块效果
- **WHEN** 用户点击 "预览分块效果"
- **THEN** MUST 调用 API 并展示统计（总块数、总字符数、平均大小）

### Requirement: Step 4 — 确认上传
第四步 SHALL 显示配置摘要和上传进度（`el-progress`）。

#### Scenario: 上传进度
- **WHEN** 用户点击 "开始上传" 按钮
- **THEN** MUST 显示 `el-progress` 进度条（30% → 60% → 100%）
- **THEN** MUST 显示状态文字（"正在上传..." → "正在处理..." → "上传成功!"）

### Requirement: 上传成功状态
上传成功后 SHALL 显示成功页面，包含 `el-result`（或自定义成功图标）、提示文字、"继续上传" 和 "检索测试" 按钮。

#### Scenario: 成功状态展示
- **WHEN** 上传完成
- **THEN** MUST 显示成功图标和 "上传成功！" 文字
- **THEN** MUST 显示知识库片段数
- **THEN** "继续上传" 按钮 MUST 重置回到 Step 1

### Requirement: RAG 检索测试
页面底部 SHALL 包含检索测试区（Element Plus 表单组件），展示带相似度分数的结果。

#### Scenario: 检索测试
- **WHEN** 用户输入查询并点击 "开始检索"
- **THEN** MUST 调用 API 并展示结果列表（来源文件、相似度百分比 + `el-tag` 颜色、内容文本）

### Requirement: 已上传文档列表
页面底部 SHALL 使用 Element Plus 组件展示文档列表，支持分页。

#### Scenario: 文档列表
- **WHEN** 有已上传文档
- **THEN** 每行 MUST 显示文件图标（颜色区分格式）、文件名、上传时间、删除按钮
- **THEN** MUST 支持 `el-pagination` 分页

#### Scenario: 删除文档
- **WHEN** 用户点击删除按钮
- **THEN** MUST 弹出 `el-message-box.confirm` 确认
- **THEN** 确认后 MUST 通过 Axios 删除文档并刷新列表

## REMOVED Requirements

### Requirement: 原型功能差异 — 当前有但原型缺失
**Reason**: 前端完全重写为 Vue 组件，`.upload-shell`、`.data-table` 等 CSS class 被 Element Plus 组件替代
**Migration**: 所有功能保留但使用 Element Plus 组件重写；清洗选项使用 el-checkbox-group；分块策略使用 el-radio-group；进度条使用 el-progress

### Requirement: 原型功能差异 — 原型有但当前不存在
**Reason**: Vue 重写以现有功能为基准
**Migration**: 多文件上传、图片压缩、邮件通知等未实现功能在后续迭代中通过 Element Plus 组件添加
