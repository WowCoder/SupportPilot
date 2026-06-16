"""
FAQ Review Service for SupportPilot

Handles FAQ generation, review workflow, and confirmation.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from ..extensions import db
from ..models.faq_entry import FAQEntry, FAQVersion
from ..models.conversation import Conversation
from ..models.chat_memory import ChatMemory
from rag.online.service import rag_service

logger = logging.getLogger(__name__)


class FAQReviewService:
    """
    Service for managing FAQ review workflow.

    Workflow:
    1. AI generates FAQ draft from conversation
    2. Tech support reviews and optionally edits
    3. Tech support confirms → synced to ChromaDB
    4. Or rejects → discarded
    """

    def __init__(self):
        pass

    def get_faq_by_id(self, faq_id: int):
        """Get FAQ entry by ID"""
        return FAQEntry.query.get(faq_id)

    def generate_faq_draft(self, session_id: int, generated_by: int) -> Optional[FAQEntry]:
        """
        Generate FAQ draft from conversation using AI.

        Args:
            session_id: Conversation session ID
            generated_by: User ID who triggered generation

        Returns:
            FAQEntry in 'pending_review' status, or None if failed
        """
        try:
            conversation = Conversation.query.get(session_id)
            if not conversation:
                logger.error(f'No conversation found for session {session_id}')
                return None

            chat_records = ChatMemory.query.filter_by(
                session_id=session_id
            ).order_by(ChatMemory.created_at.asc()).limit(20).all()

            if not chat_records:
                logger.error(f'No chat records found for session {session_id}')
                return None

            conversation_text = '\n'.join([
                f"{r.sender_type}: {r.content}"
                for r in chat_records
            ])

            # Extract Q&A using LLM
            question, answer = self._extract_qa_from_conversation(conversation_text)
            if not question or not answer:
                logger.warning(f'Failed to extract Q&A from session {session_id}')
                return None

            faq = FAQEntry(
                question=question,
                answer=answer,
                category='',
                status='pending_review',
                source_session_id=session_id,
                created_by=generated_by
            )
            db.session.add(faq)
            db.session.commit()

            logger.info(f'Generated FAQ draft {faq.id} for session {session_id}')
            return faq

        except Exception as e:
            logger.error(f'Error generating FAQ draft: {e}', exc_info=True)
            db.session.rollback()
            return None

    def _extract_qa_from_conversation(self, conversation_text: str):
        """Extract Q&A from conversation using LLM. Returns (question, answer) tuple."""
        from llm.llm_client import llm_client

        messages = [
            {
                "role": "system",
                "content": "你是一个FAQ提取专家。从客服对话中提取一个核心问答对。规则：1.问题应简洁明确；2.答案应准确完整；3.去除客套话；4.输出必须为JSON格式：{\"question\": \"...\", \"answer\": \"...\"}"
            },
            {
                "role": "user",
                "content": f"请从以下对话中提取FAQ：\n\n{conversation_text}"
            }
        ]

        try:
            content = llm_client.generate(messages, temperature=0.3, max_tokens=1024)
            if content and not content.startswith("抱歉"):
                import json
                import re
                content = content.strip()
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    return parsed.get('question', ''), parsed.get('answer', '')
        except Exception as e:
            logger.warning(f'LLM FAQ extraction failed: {e}, using fallback')

        return self._fallback_extraction(conversation_text)

    def _fallback_extraction(self, conversation_text: str):
        """Simple fallback: take first user question as Q, last AI answer as A."""
        lines = conversation_text.split('\n')
        questions = [l.replace('user: ', '') for l in lines if l.startswith('user: ')]
        answers = [l.replace('ai: ', '') for l in lines if l.startswith('ai: ')]

        question = questions[0] if questions else ''
        answer = answers[-1] if answers else ''
        return question, answer

    def update_faq_draft(self, faq_id: int, question: str, answer: str,
                         category: str, user_id: int, change_reason: str = None) -> bool:
        """
        Update FAQ draft with edits from tech support.

        Args:
            faq_id: FAQ entry ID
            question: Updated question
            answer: Updated answer
            category: Category
            user_id: User ID making the change
            change_reason: Optional reason for change

        Returns:
            True if successful
        """
        faq = FAQEntry.query.get(faq_id)
        if not faq:
            logger.error(f'FAQ {faq_id} not found')
            return False

        if faq.status != 'pending_review':
            logger.warning(f'FAQ {faq_id} is not pending review (status={faq.status})')
            return False

        # Add version record before updating
        version = faq.add_version(user_id, change_reason)
        db.session.add(version)

        # Update FAQ
        faq.question = question
        faq.answer = answer
        faq.category = category

        db.session.commit()
        logger.info(f'Updated FAQ draft {faq_id}')
        return True

    def confirm_faq(self, faq_id: int, user_id: int) -> bool:
        """
        Confirm FAQ and sync to ChromaDB.

        Args:
            faq_id: FAQ entry ID
            user_id: User ID confirming the FAQ

        Returns:
            True if successful, False otherwise
        """
        faq = FAQEntry.query.get(faq_id)
        if not faq:
            logger.error(f'FAQ {faq_id} not found')
            return False

        if faq.status != 'pending_review':
            logger.warning(f'FAQ {faq_id} is not pending review (status={faq.status})')
            return False

        # Sync to ChromaDB
        from rag.utils.faq_vector_sync import sync_faq_to_chroma
        try:
            chroma_doc_ids = sync_faq_to_chroma(faq)
            if not chroma_doc_ids:
                logger.error(f'Failed to sync FAQ {faq_id} to ChromaDB')
                return False

            # Mark as confirmed
            faq.mark_as_confirmed(user_id, chroma_doc_ids)

            # Add final version record
            version = faq.add_version(user_id, 'Confirmed and synced to ChromaDB')
            db.session.add(version)

            db.session.commit()
            logger.info(f'FAQ {faq_id} confirmed and synced to ChromaDB')
            return True

        except Exception as e:
            logger.error(f'Error confirming FAQ {faq_id}: {e}', exc_info=True)
            db.session.rollback()
            return False

    def reject_faq(self, faq_id: int, user_id: int, reason: str = None) -> bool:
        """
        Reject FAQ draft.

        Args:
            faq_id: FAQ entry ID
            user_id: User ID rejecting the FAQ
            reason: Optional rejection reason

        Returns:
            True if successful
        """
        faq = FAQEntry.query.get(faq_id)
        if not faq:
            logger.error(f'FAQ {faq_id} not found')
            return False

        if faq.status != 'pending_review':
            logger.warning(f'FAQ {faq_id} is not pending review (status={faq.status})')
            return False

        faq.mark_as_rejected()

        # Add version record with rejection reason
        version = faq.add_version(user_id, f'Rejected: {reason}' if reason else 'Rejected')
        db.session.add(version)

        db.session.commit()
        logger.info(f'FAQ {faq_id} rejected by user {user_id}')
        return True

    def get_pending_reviews(self, limit: int = 20) -> List[FAQEntry]:
        """
        Get FAQ entries pending review.

        Args:
            limit: Maximum number to return

        Returns:
            List of FAQEntry objects
        """
        return FAQEntry.query.filter_by(
            status='pending_review'
        ).order_by(FAQEntry.created_at.desc()).limit(limit).all()


# Singleton instance
faq_review_service = FAQReviewService()
