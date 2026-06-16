"""
Faithfulness Check Node for Agentic RAG system.

Verifies that the generated answer is faithful to the retrieved documents.
Detects hallucinations where the LLM invents information not present in
the source documents.
"""
import logging
from typing import Any, Dict, List, Optional

from rag.online.pipeline.state import AgentStateDict
from rag.utils.config import get_config

logger = logging.getLogger(__name__)


class FaithfulnessCheckNode:
    """
    Checks if generated answer is grounded in retrieved documents.

    Uses LLM to decompose answer into claims and verify each against
    the source documents. Triggers re-retrieval if faithfulness is low.
    """

    def __init__(self):
        self.config = get_config()
        self.threshold = self.config.get('agent.faithfulness_threshold', 0.8)

    def _check_with_llm(self, query: str, answer: str,
                        documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use LLM to check answer faithfulness.

        Returns dict with 'faithful_count', 'total_claims', 'hallucinations', 'score'.
        """
        # Build document context
        doc_context = ''
        for i, doc in enumerate(documents[:5], 1):
            content = doc.get('content', '')[:300]
            doc_context += f"[文档{i}]: {content}\n\n"

        prompt = f"""评估以下答案是否忠实于提供的文档内容。逐一检查答案中的每个陈述是否可以在文档中找到依据。

文档内容：
{doc_context}

用户问题：{query}

生成的答案：
{answer}

请分析答案中的每个陈述，输出JSON格式：
{{
  "claims": [
    {{"statement": "答案中的陈述1", "faithful": true/false, "evidence": "文档中的依据或'无'"}},
    ...
  ],
  "faithful_count": 有依据的陈述数量,
  "total_claims": 陈述总数,
  "hallucinations": ["无依据的陈述1", ...]
}}

只输出JSON，不要其他文字。"""

        try:
            from llm.llm_client import llm_client

            messages = [{"role": "user", "content": prompt}]
            response = llm_client.generate(messages, temperature=0, max_tokens=512)

            if response:
                import json
                response = response.strip()
                if response.startswith('```'):
                    lines = response.split('\n')
                    response = '\n'.join(lines[1:-1])
                return json.loads(response)
        except Exception as e:
            logger.warning(f'Faithfulness check failed: {e}')

        return {'faithful_count': 0, 'total_claims': 1, 'hallucinations': ['check failed'], 'score': 0.0}

    def process(self, state: AgentStateDict) -> AgentStateDict:
        """
        Verify answer faithfulness to retrieved documents.

        If faithfulness is below threshold, flags for re-retrieval.
        """
        query = state.get('query', '')
        answer = state.get('final_answer', '')
        documents = list(state.get('retrieval_results', []))

        if not answer or not documents:
            state['faithfulness_score'] = 1.0  # No answer to check
            return state

        result = self._check_with_llm(query, answer, documents)

        faithful_count = result.get('faithful_count', 0)
        total_claims = result.get('total_claims', 1)
        hallucinations = result.get('hallucinations', [])

        score = faithful_count / max(total_claims, 1)

        state['faithfulness_score'] = score
        state['hallucination_flags'] = list(hallucinations) if hallucinations else []

        if score < self.threshold:
            logger.warning(f'Faithfulness check FAILED: score={score:.2f} '
                          f'({faithful_count}/{total_claims}) hallucinations: {hallucinations}')
        else:
            logger.info(f'Faithfulness check passed: score={score:.2f} '
                       f'({faithful_count}/{total_claims})')

        return state


faithfulness_check_node = FaithfulnessCheckNode()
