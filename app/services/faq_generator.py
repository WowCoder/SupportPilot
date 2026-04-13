"""
FAQ Generator Service for SupportPilot

Generates FAQ entries from closed conversations and manages vector storage.
"""
import logging
from typing import List, Optional, Dict, Tuple
import hashlib

from ..extensions import db
from ..models.chat_memory import ChatMemory
from ..models.faq_entry import FAQEntry
from ..models.conversation import Conversation
from ..config import get_config

logger = logging.getLogger(__name__)


class FAQGenerator:
    """
    Service for generating FAQ entries from conversations.

    Features:
    - Generate FAQ from conversation window + summaries
    - Similarity check against existing FAQs
    - Save to both SQLite and ChromaDB
    """

    def __init__(self):
        self.config = get_config()
        self.similarity_threshold = getattr(self.config, 'FAQ_SIMILARITY_THRESHOLD', 0.9)
        self.compression_ratio_target = getattr(self.config, 'SUMMARY_COMPRESSION_RATIO_TARGET', 10)

    def generate_from_session(self, session_id: int) -> Dict:
        """
        Generate FAQ entries from a closed conversation.

        Args:
            session_id: Conversation session ID

        Returns:
            Dict with generation result:
            {
                'success': bool,
                'faq_count': int,
                'qa_pairs': List[{'question': str, 'answer': str}],
                'duplicates_skipped': int
            }
        """
        # Get conversation window records
        window_records = ChatMemory.query.filter_by(
            session_id=session_id,
            status='active'
        ).order_by(ChatMemory.created_at.asc()).all()

        # Get session summaries
        summaries = ChatMemory.query.filter_by(
            session_id=session_id,
            status='compressed'
        ).order_by(ChatMemory.compressed_at.asc()).all()

        # Build context from window + summaries
        context_parts = []

        # Add summaries (early background)
        for summary in summaries:
            if summary.summary:
                context_parts.append(f"[历史摘要] {summary.summary}")

        # Add window records (latest details)
        for record in window_records:
            sender = record.sender_type
            content = record.content
            context_parts.append(f"[{sender}] {content}")

        full_context = "\n\n".join(context_parts)

        if not full_context.strip():
            logger.warning(f'No content found for session {session_id}')
            return {
                'success': False,
                'error': 'No conversation content found',
                'faq_count': 0,
                'qa_pairs': [],
                'duplicates_skipped': 0
            }

        # Generate Q&A pairs using LLM
        qa_pairs = self._extract_qa_pairs(full_context)

        if not qa_pairs:
            logger.warning(f'Failed to extract Q&A pairs from session {session_id}')
            return {
                'success': False,
                'error': 'Failed to extract Q&A pairs',
                'faq_count': 0,
                'qa_pairs': [],
                'duplicates_skipped': 0
            }

        # Process each Q&A pair
        saved_count = 0
        duplicates_skipped = 0

        for qa in qa_pairs:
            question = qa['question']
            answer = qa['answer']

            # Check for duplicates
            is_duplicate, duplicate_id = self.check_similarity(question)

            if is_duplicate:
                logger.info(f'FAQ duplicate detected: "{question[:50]}..." matches existing FAQ {duplicate_id}')
                duplicates_skipped += 1
                continue

            # Save FAQ
            self.save_faq(question, answer, session_id)
            saved_count += 1

        logger.info(f'Generated {saved_count} FAQ entries from session {session_id} ({duplicates_skipped} duplicates skipped)')

        return {
            'success': True,
            'faq_count': saved_count,
            'qa_pairs': qa_pairs,
            'duplicates_skipped': duplicates_skipped
        }

    def _extract_qa_pairs(self, context: str) -> List[Dict]:
        """
        Extract Q&A pairs from conversation context using LLM.

        Args:
            context: Full conversation context (window + summaries)

        Returns:
            List of {'question': str, 'answer': str} dicts
        """
        from api.qwen_api import qwen_api

        system_prompt = """你是一个 FAQ 提取专家。你的任务是从客服对话中提取高质量的 Q&A 对。

规则：
- 提取客户关心的典型问题
- 答案应准确、简洁、完整
- 去除对话中的客套话和无关内容
- 每个 Q&A 对应该是独立的、可理解的
- 输出格式为 JSON 数组：[{"question": "...", "answer": "..."}]

如果对话中没有值得提取的 Q&A，返回空数组 []。"""

        user_prompt = f"""请从以下客服对话中提取 Q&A 对：

{context}

提取的 Q&A 对（JSON 格式）："""

        try:
            import json
            import os
            import requests

            api_key = os.environ.get('QWEN_API_KEY')
            if not api_key:
                logger.warning('QWEN_API_KEY not configured, cannot generate FAQ')
                return []

            api_url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }

            data = {
                "model": "qwen-turbo",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2048
            }

            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()

                # Parse JSON response
                try:
                    # Try to find JSON array in response
                    import re
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        qa_pairs = json.loads(json_match.group())
                        logger.info(f'Extracted {len(qa_pairs)} Q&A pairs')
                        return qa_pairs
                    else:
                        logger.warning(f'No JSON array found in response: {content[:200]}...')
                        return []
                except json.JSONDecodeError as e:
                    logger.error(f'Failed to parse JSON response: {e}')
                    return []
            else:
                logger.warning(f'Unexpected API response format: {result}')
                return []

        except requests.exceptions.Timeout:
            logger.error('FAQ extraction timeout')
            return []
        except Exception as e:
            logger.error(f'FAQ extraction failed: {e}', exc_info=True)
            return []

    def check_similarity(self, question: str, threshold: float = None) -> Tuple[bool, Optional[int]]:
        """
        Check if a question is similar to existing FAQs.

        Args:
            question: Question to check
            threshold: Similarity threshold (default: similarity_threshold from config)

        Returns:
            Tuple of (is_duplicate: bool, duplicate_of_id: Optional[int])
        """
        if threshold is None:
            threshold = self.similarity_threshold

        # Get all existing FAQs
        existing_faqs = FAQEntry.query.filter_by(is_duplicate=False).all()

        if not existing_faqs:
            return False, None

        # Use RAG to find similar FAQs
        from rag.rag_utils import rag_utils

        try:
            # Search for similar FAQs in ChromaDB
            results = rag_utils.retrieve_relevant_info(question, k=5, similarity_threshold=0.5)

            if not results:
                return False, None

            # Check if any result exceeds threshold
            for result in results:
                if result.get('similarity', 0) >= threshold:
                    # Find the FAQ entry with this content
                    similar_faq = FAQEntry.query.filter_by(
                        question=result['content']
                    ).first()

                    if similar_faq:
                        logger.info(f'Found similar FAQ {similar_faq.id} (similarity: {result["similarity"]:.2f})')
                        return True, similar_faq.id

            return False, None

        except Exception as e:
            logger.error(f'Similarity check failed: {e}', exc_info=True)
            # On error, assume not duplicate to avoid losing FAQs
            return False, None

    def save_faq(self, question: str, answer: str, source_session_id: int, chroma_doc_id: str = None) -> Optional[FAQEntry]:
        """
        Save a FAQ entry to both SQLite and ChromaDB.

        Args:
            question: FAQ question
            answer: FAQ answer
            source_session_id: Source conversation session ID
            chroma_doc_id: Optional ChromaDB document ID (for updates)

        Returns:
            Created FAQEntry or None
        """
        from rag.rag_utils import rag_utils

        # Create FAQ entry
        faq = FAQEntry(
            question=question,
            answer=answer,
            source_session_id=source_session_id
        )

        db.session.add(faq)
        db.session.flush()  # Get ID

        # Add to ChromaDB
        try:
            content = f"Q: {question}\nA: {answer}"
            doc_id = chroma_doc_id or f"faq_{faq.id}_{hashlib.md5(question.encode()).hexdigest()[:16]}"

            rag_utils.collection.add(
                documents=[content],
                ids=[doc_id],
                metadatas=[{
                    'source': 'faq_from_session',
                    'session_id': str(source_session_id),
                    'faq_id': str(faq.id),
                    'type': 'qa_pair'
                }]
            )

            faq.chroma_doc_id = doc_id
            faq.mark_as_unique(chroma_doc_id=doc_id)

            db.session.commit()

            logger.info(f'Saved FAQ {faq.id} to database and ChromaDB (doc_id: {doc_id})')
            return faq

        except Exception as e:
            logger.error(f'Failed to save FAQ to ChromaDB: {e}', exc_info=True)
            db.session.rollback()
            return None

    def delete_faq(self, faq_id: int) -> bool:
        """
        Delete a FAQ entry from both SQLite and ChromaDB.

        Args:
            faq_id: FAQ entry ID

        Returns:
            True if successful
        """
        from rag.rag_utils import rag_utils

        faq = FAQEntry.query.get(faq_id)
        if not faq:
            return False

        # Remove from ChromaDB
        if faq.chroma_doc_id:
            try:
                rag_utils.collection.delete(ids=[faq.chroma_doc_id])
                logger.info(f'Deleted FAQ {faq_id} from ChromaDB (doc_id: {faq.chroma_doc_id})')
            except Exception as e:
                logger.error(f'Failed to delete from ChromaDB: {e}')

        # Remove from SQLite
        db.session.delete(faq)
        db.session.commit()

        logger.info(f'Deleted FAQ {faq_id}')
        return True


# Global instance
faq_generator = FAQGenerator()
