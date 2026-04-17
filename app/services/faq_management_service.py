"""
FAQ Management Service for SupportPilot

Handles CRUD operations for FAQ entries.
"""
import logging
from typing import Optional, List, Dict, Any

from ..extensions import db
from ..models.faq_entry import FAQEntry, FAQVersion
from ..models.user import User
from rag.faq_vector_sync import sync_faq_to_chroma, remove_faq_from_chroma, update_faq_in_chroma

logger = logging.getLogger(__name__)


class FAQManagementService:
    """
    Service for managing FAQ entries.

    Features:
    - CRUD operations for FAQ entries
    - Search and filter
    - Version history tracking
    - ChromaDB synchronization
    """

    def get_faq_by_id(self, faq_id: int) -> Optional[FAQEntry]:
        """Get FAQ entry by ID"""
        return FAQEntry.query.get(faq_id)

    def get_faq(self, faq_id: int) -> Optional[FAQEntry]:
        """
        Get FAQ entry by ID.

        Args:
            faq_id: FAQ entry ID

        Returns:
            FAQEntry or None
        """
        return FAQEntry.query.get(faq_id)

    def get_all_faqs(self, status: str = None, category: str = None,
                     search: str = None, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """
        Get all FAQ entries with optional filtering.

        Args:
            status: Filter by status ('confirmed', 'pending_review', 'rejected', 'draft')
            category: Filter by category
            search: Search keyword in question/answer
            page: Page number
            per_page: Items per page

        Returns:
            Dict with 'items' and 'pagination'
        """
        query = FAQEntry.query

        if status:
            query = query.filter_by(status=status)

        if category:
            query = query.filter_by(category=category)

        if search:
            search_pattern = f'%{search}%'
            query = query.filter(
                (FAQEntry.question.like(search_pattern)) |
                (FAQEntry.answer.like(search_pattern))
            )

        pagination = query.order_by(FAQEntry.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        return {
            'items': pagination.items,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'total': pagination.total,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        }

    def create_faq(self, question: str, answer: str, category: str,
                   user_id: int, status: str = 'draft') -> Optional[FAQEntry]:
        """
        Create a new FAQ entry.

        Args:
            question: FAQ question
            answer: FAQ answer
            category: FAQ category
            user_id: User ID creating the FAQ
            status: Initial status ('draft' or 'confirmed')

        Returns:
            FAQEntry or None if failed
        """
        try:
            faq = FAQEntry(
                question=question,
                answer=answer,
                category=category,
                status=status,
                created_by=user_id
            )
            db.session.add(faq)

            # Add initial version
            version = faq.add_version(user_id, 'Initial creation')
            db.session.add(version)

            # If confirmed, sync to ChromaDB
            if status == 'confirmed':
                chroma_doc_ids = sync_faq_to_chroma(faq)
                if chroma_doc_ids:
                    faq.mark_as_confirmed(user_id, chroma_doc_ids)
                else:
                    logger.warning(f'Failed to sync FAQ {faq.id} to ChromaDB')

            db.session.commit()
            logger.info(f'Created FAQ {faq.id}')
            return faq

        except Exception as e:
            logger.error(f'Error creating FAQ: {e}', exc_info=True)
            db.session.rollback()
            return None

    def update_faq(self, faq_id: int, question: str = None, answer: str = None,
                   category: str = None, user_id: int = None,
                   change_reason: str = None) -> bool:
        """
        Update an existing FAQ entry.

        Args:
            faq_id: FAQ entry ID
            question: Updated question (optional)
            answer: Updated answer (optional)
            category: Updated category (optional)
            user_id: User ID making the change
            change_reason: Reason for change

        Returns:
            True if successful
        """
        faq = self.get_faq(faq_id)
        if not faq:
            logger.error(f'FAQ {faq_id} not found')
            return False

        # Track what changed
        changes = []

        if question is not None and faq.question != question:
            faq.question = question
            changes.append('question')

        if answer is not None and faq.answer != answer:
            faq.answer = answer
            changes.append('answer')

        if category is not None:
            faq.category = category
            changes.append('category')

        if not changes:
            return True  # No changes needed

        # Add version record
        if user_id:
            reason = change_reason or f'Updated: {", ".join(changes)}'
            version = faq.add_version(user_id, reason)
            db.session.add(version)

        # If confirmed, update ChromaDB
        if faq.status == 'confirmed':
            try:
                update_faq_in_chroma(faq)
                logger.info(f'Updated ChromaDB for FAQ {faq_id}')
            except Exception as e:
                logger.error(f'Error updating ChromaDB: {e}')

        db.session.commit()
        logger.info(f'Updated FAQ {faq_id}: {", ".join(changes)}')
        return True

    def delete_faq(self, faq_id: int) -> bool:
        """
        Delete an FAQ entry (soft delete).

        Args:
            faq_id: FAQ entry ID

        Returns:
            True if successful
        """
        faq = self.get_faq(faq_id)
        if not faq:
            logger.error(f'FAQ {faq_id} not found')
            return False

        # Remove from ChromaDB
        try:
            remove_faq_from_chroma(faq)
            logger.info(f'Removed FAQ {faq_id} from ChromaDB')
        except Exception as e:
            logger.error(f'Error removing from ChromaDB: {e}')

        # Soft delete - mark status
        faq.status = 'deleted'

        db.session.commit()
        logger.info(f'Deleted FAQ {faq_id}')
        return True

    def hard_delete_faq(self, faq_id: int) -> bool:
        """
        Permanently delete an FAQ entry (admin only).

        Args:
            faq_id: FAQ entry ID

        Returns:
            True if successful
        """
        faq = self.get_faq(faq_id)
        if not faq:
            return False

        # Remove from ChromaDB first
        try:
            remove_faq_from_chroma(faq)
        except Exception as e:
            logger.error(f'Error removing from ChromaDB: {e}')

        # Delete from database
        db.session.delete(faq)
        db.session.commit()
        return True

    def get_version_history(self, faq_id: int) -> List[FAQVersion]:
        """
        Get version history for an FAQ entry.

        Args:
            faq_id: FAQ entry ID

        Returns:
            List of FAQVersion records
        """
        return FAQVersion.query.filter_by(faq_id=faq_id)\
            .order_by(FAQVersion.created_at.desc()).all()

    def bulk_delete(self, faq_ids: List[int]) -> Dict[str, int]:
        """
        Delete multiple FAQ entries.

        Args:
            faq_ids: List of FAQ IDs to delete

        Returns:
            Dict with 'success' and 'failed' counts
        """
        success = 0
        failed = 0

        for faq_id in faq_ids:
            if self.delete_faq(faq_id):
                success += 1
            else:
                failed += 1

        return {'success': success, 'failed': failed}


# Singleton instance
faq_management_service = FAQManagementService()
