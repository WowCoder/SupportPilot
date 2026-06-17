## ADDED Requirements

### Requirement: FAQ 管理后台

系统应为技术支持提供 FAQ 管理界面，支持查看所有 FAQ、增删改操作，并实时同步到向量数据库。

#### Scenario: 查看 FAQ 列表
- **WHEN** 技术支持访问 FAQ 管理页面
- **THEN** 系统展示所有 FAQ 条目，包含问题、答案、分类、状态（已确认/待审核）、创建时间

#### Scenario: FAQ 搜索和筛选
- **WHEN** 技术支持输入搜索关键词或选择筛选条件
- **THEN** 系统按关键词搜索问题/答案，或按分类、状态筛选 FAQ 列表

#### Scenario: 新增 FAQ
- **WHEN** 技术支持点击"新增 FAQ"并填写问题、答案、分类
- **THEN** 系统保存 FAQ 并向量化到 ChromaDB，状态为"已确认"

#### Scenario: 编辑 FAQ
- **WHEN** 技术支持编辑已有 FAQ 并保存
- **THEN** 系统更新数据库记录，同时更新 ChromaDB 中对应的向量记录，记录版本历史

#### Scenario: 删除 FAQ
- **WHEN** 技术支持删除 FAQ
- **THEN** 系统从数据库标记为"已删除"，同时从 ChromaDB 中移除对应向量记录

#### Scenario: FAQ 批量操作
- **WHEN** 技术支持选择多个 FAQ 并执行批量删除
- **THEN** 系统批量处理数据库和向量数据库，返回成功/失败统计

#### Scenario: FAQ 版本历史
- **WHEN** 技术支持查看 FAQ 详情
- **THEN** 系统展示该 FAQ 的所有历史版本（修改时间、修改人、修改原因）
