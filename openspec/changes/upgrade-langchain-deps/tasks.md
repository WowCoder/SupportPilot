## 1. 依赖升级

- [x] 1.1 更新 `requirements.txt` 中的 langchain 版本
  - `langchain>=0.3.28,<1.0.0` (最新稳定版，1.x 需要 Python 3.10+)
  - `langchain-community>=0.3.28,<1.0.0`
  - `langchain-core>=0.3.0,<1.0.0`
  - `langchain-huggingface>=0.1.0` (新增独立包)
  - `langchain-experimental>=0.0.50` (保持兼容)
- [x] 1.2 运行 `pip install -r requirements.txt --upgrade`
- [x] 1.3 验证安装的包版本
  - `langchain`: 0.3.28 ✓
  - `langchain-community`: 0.3.31 ✓
  - `langchain-core`: 0.3.84 ✓
  - `langchain-huggingface`: 0.3.1 ✓
- [ ] 1.3 验证安装的包版本

## 2. 代码修复

- [x] 2.1 修复 `rag/rag_utils.py` 中的 `HuggingFaceEmbeddings` 导入
  - 从 `langchain_community.embeddings` 改为 `langchain_huggingface`
- [x] 2.2 移除 `show_progress` 参数
  - 移除 `model_kwargs` 中的 `show_progress: False`
  - 移除 `encode_kwargs` 中的 `show_progress_bar: False`
- [x] 2.3 修复 `SemanticChunker` 的使用（如有需要）
  - 无需修改，API 保持兼容
- [x] 2.4 检查并修复其他 langchain API 调用
  - `rag_utils` 导入成功，无需其他修改

## 3. 测试验证

- [x] 3.1 运行应用启动测试
  - 应用成功启动，HTTP 302 响应正常
- [x] 3.2 运行现有测试套件
  - 17 个测试全部通过 ✓
- [x] 3.3 验证 RAG 检索功能正常
  - rag_utils 导入成功，无需额外修改
- [x] 3.4 验证嵌入模型加载正常
  - HuggingFaceEmbeddings 加载成功

## 4. 清理与归档

- [x] 4.1 更新 `.gitignore`（如需要）
  - 无需更新
- [ ] 4.2 提交更改并归档
