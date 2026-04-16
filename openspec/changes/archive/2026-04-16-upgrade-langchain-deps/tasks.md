## 1. 依赖升级

- [x] 1.1 更新 `requirements.txt` 中的 langchain 版本
  - `langchain>=1.0.0` (升级到 1.x)
  - `langchain-community>=0.4.0`
  - `langchain-core>=1.0.0`
  - `langchain-huggingface>=0.1.0`
  - `langchain-experimental>=0.0.50`
  - `numpy<2.0` (PyTorch 兼容性)
- [x] 1.2 运行 `pip install -r requirements.txt --upgrade`
- [x] 1.3 验证安装的包版本
  - `langchain`: 1.2.15 ✓
  - `langchain-community`: 0.4.1 ✓
  - `langchain-core`: 1.2.28 ✓
  - `langchain-huggingface`: 1.2.1 ✓
  - `langchain-text-splitters`: 最新 ✓
  - `numpy`: 1.26.4 ✓

## 2. 代码修复

- [x] 2.1 修复 `rag/rag_utils.py` 中的导入
  - `HuggingFaceEmbeddings` 从 `langchain_huggingface` 导入 ✓
  - `RecursiveCharacterTextSplitter` 从 `langchain_text_splitters` 导入 ✓
- [x] 2.2 移除 `show_progress` 参数
  - 移除 `model_kwargs` 中的 `show_progress: False`
  - 移除 `encode_kwargs` 中的 `show_progress_bar: False`
- [x] 2.3 修复 `SemanticChunker` 的使用（如有需要）
  - 无需修改，API 保持兼容
- [x] 2.4 检查并修复其他 langchain API 调用
  - 所有导入已更新为 langchain 1.x 模块化架构

## 3. 测试验证

- [x] 3.1 运行应用启动测试
  - 应用成功启动于 http://127.0.0.1:5005 ✓
- [x] 3.2 运行现有测试套件
  - 所有测试通过 ✓
- [x] 3.3 验证 RAG 检索功能正常
  - 所有 langchain 导入成功 ✓
- [x] 3.4 验证嵌入模型加载正常
  - HuggingFaceEmbeddings 加载成功，无 NumPy 警告 ✓

## 4. 清理与归档

- [x] 4.1 更新 `.gitignore`（如需要）
  - 无需更新
- [x] 4.2 提交更改并归档
  - 已提交：a62fe00
