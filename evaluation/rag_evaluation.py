"""LLM-as-Judge for RAG retrieval quality evaluation."""
import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """你是一个 RAG 检索质量评估专家。你的任务是评估检索系统返回的文档对用户查询的匹配程度。

请从以下三个维度评分（每个维度 1-5 分，1=最差，5=最好）：

1. **relevance（相关性）**：检索到的文档与用户问题的直接相关程度。是否能回答这个问题？
2. **completeness（完整性）**：检索结果是否覆盖了回答问题所需的所有关键信息？有没有遗漏？
3. **noise（噪声）**：检索结果中是否混入了无关文档？是否有"搜了等于没搜"的内容？

请严格按以下 JSON 格式输出，不要包含其他文字：
{
  "relevance": <1-5 整数>,
  "completeness": <1-5 整数>,
  "noise": <1-5 整数>,
  "reason": "<每个维度一句话说明>"
}"""


def judge_retrieval(query: str, results: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Evaluate retrieval quality using LLM-as-Judge.

    Args:
        query: Original user query
        results: List of retrieval results with 'content' and 'similarity' keys

    Returns:
        Dict with judge_score (dict) and judge_reason (str), or None on failure
    """
    if not results:
        return {"judge_score": None, "judge_reason": "无检索结果，无法评估"}

    # Build context for judge
    chunks_text = []
    for i, r in enumerate(results):
        similarity = r.get('similarity', 0)
        content = r.get('content', '')
        chunks_text.append(f"[文档 {i + 1}] 相似度: {similarity:.3f}\n{content[:800]}")

    judge_query = f"用户查询：{query}\n\n检索到的文档：\n" + "\n\n".join(chunks_text)

    try:
        from llm.llm_client import llm_client

        response = llm_client.chat(
            query=judge_query,
            context=None,
            system_prompt=JUDGE_SYSTEM_PROMPT,
            temperature=0.1,
            max_tokens=500
        )

        # Try to parse JSON from response
        parsed = _parse_judge_response(response)
        if parsed:
            return {
                "judge_score": {
                    "relevance": parsed["relevance"],
                    "completeness": parsed["completeness"],
                    "noise": parsed["noise"]
                },
                "judge_reason": parsed["reason"]
            }
        else:
            return {"judge_score": None, "judge_reason": f"评分失败：无法解析 LLM 响应 ({response[:200]})"}

    except Exception as e:
        logger.error(f"LLM-as-Judge failed: {e}", exc_info=True)
        return {"judge_score": None, "judge_reason": f"评分失败：{str(e)[:200]}"}


def _parse_judge_response(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from LLM judge response."""
    # Try direct parse
    try:
        data = json.loads(response)
        if all(k in data for k in ['relevance', 'completeness', 'noise']):
            return data
    except json.JSONDecodeError:
        pass

    # Try to extract JSON block
    match = re.search(r'\{[\s\S]*?"relevance"[\s\S]*?"noise"[\s\S]*?\}', response)
    if match:
        try:
            data = json.loads(match.group())
            if all(k in data for k in ['relevance', 'completeness', 'noise']):
                return data
        except json.JSONDecodeError:
            pass

    return None
