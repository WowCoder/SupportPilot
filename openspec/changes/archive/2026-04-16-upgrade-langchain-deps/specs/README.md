# LangChain 依赖升级

本次升级不涉及新功能或规格变更，仅依赖版本升级和代码兼容性修复。

## 升级内容

- `langchain`: 0.0.350 → 0.3.x
- `langchain-community`: 0.0.10 → 0.3.x
- 新增 `langchain_huggingface`: >=0.1.0

## 代码修复

- `rag/rag_utils.py`: 更新 `HuggingFaceEmbeddings` 导入和参数
- 移除 `show_progress` 参数
