## Why

当前 `langchain-community==0.0.10` 和 `langchain==0.0.350` 版本过旧，与 Python 3.9 存在 metaclass 冲突，导致应用无法启动和测试无法运行。需要升级到 langchain 1.x 最新版本并修复所有兼容性代码。

## What Changes

- **dependencies**: 升级 langchain 相关包到 1.x 版本
  - `langchain`: 0.0.350 → `>=1.0.0` (1.x 最新版)
  - `langchain-community`: 0.0.10 → `>=1.0.0`
  - `langchain-core`: → `>=1.0.0`
  - 新增 `langchain-huggingface`: >=0.1.0 (HuggingFace 组件独立包)
- **代码修复**: 更新已弃用的 API 调用
  - `HuggingFaceEmbeddings` 导入路径和参数
  - `SemanticChunker` 使用方式
  - 移除 `pydantic_v1` 兼容性导入
  - 适配 1.x API 变更
- **requirements.txt**: 更新依赖版本约束
- **测试验证**: 确保所有现有测试通过

## Capabilities

### New Capabilities
（无新增功能，仅依赖升级和代码兼容）

### Modified Capabilities
（无修改的功能规格，仅内部实现调整）

## Impact

- **受影响文件**:
  - `requirements.txt`: 依赖版本更新
  - `rag/rag_utils.py`: HuggingFaceEmbeddings 和 SemanticChunker 使用
  - 可能影响其他使用 langchain API 的模块

- **兼容性**:
  - 保持现有功能行为不变
  - 仅修复已弃用 API 的调用方式
  - 测试需全部通过

- **风险**:
  - langchain API 变更可能导致意外行为
  - 需要完整测试验证
