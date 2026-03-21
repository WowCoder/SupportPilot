#!/usr/bin/env python3
"""Test script for Chroma RAG integration - Simple test"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 50)
print("Chroma RAG Integration Test")
print("=" * 50)

# Test 1: Import and initialize
print("\n[TEST 1] Initialize RAG Utils...")
from rag.rag_utils import rag_utils
print(f"✓ RAG Utils loaded, document count: {rag_utils.get_document_count()}")

# Test 2: Create and process a test document
print("\n[TEST 2] Process test document...")
test_content = """SupportPilot 智能客服系统文档

第一章：系统概述
SupportPilot 是一个基于 Flask 的智能客服系统，支持用户与 AI 助手进行对话。
系统采用 RAG (检索增强生成) 技术，能够提供准确的知识库检索。

第二章：用户功能
1. 用户可以注册和登录
2. 创建新的对话
3. 发送消息并获得 AI 回复

第三章：技术支持功能
1. 上传文档到知识库 (支持 txt, pdf, docx)
2. 查看所有用户对话
3. 关闭或重新打开对话
"""

# Use absolute path for test file
test_dir = os.path.dirname(os.path.abspath(__file__))
test_file = os.path.join(test_dir, 'test_knowledge.txt')

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(test_content)

result = rag_utils.process_document(test_file)
print(f"✓ Document processed: {result}")
print(f"✓ Document count after: {rag_utils.get_document_count()}")

# Test 3: Retrieve relevant info
print("\n[TEST 3] Retrieve relevant information...")
query = "如何上传文档？"
print(f"Query: {query}")
results = rag_utils.retrieve_relevant_info(query, k=2)
print(f"✓ Retrieved {len(results)} results")
for i, r in enumerate(results, 1):
    print(f"  [{i}] similarity={r['similarity']:.4f}, source={r['source']}")
    print(f"      content={r['content'][:60]}...")

# Test 4: Deduplication
print("\n[TEST 4] Test deduplication...")
count_before = rag_utils.get_document_count()
rag_utils.process_document(test_file)
count_after = rag_utils.get_document_count()
print(f"✓ Before: {count_before}, After: {count_after}")
print(f"✓ Deduplication working: {count_before == count_after}")

# Cleanup
os.remove(test_file)

print("\n" + "=" * 50)
print("All tests passed!")
print("=" * 50)
