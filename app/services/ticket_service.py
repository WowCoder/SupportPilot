"""
Ticket Service for SupportPilot

Handles ticket lifecycle management, round counting, and human handoff.
"""
import logging
from datetime import datetime
from typing import Optional, Tuple

from ..extensions import db
from ..models.support_ticket import SupportTicket
from ..models.chat_memory import ChatMemory
from ..config import get_config

logger = logging.getLogger(__name__)


class TicketService:
    """
    Service for managing support tickets.

    Features:
    - Ticket lifecycle management (open → pending_human → closed)
    - Round counting for human handoff trigger
    - Ticket status tracking
    """

    def __init__(self):
        self.config = get_config()
        self.handoff_threshold = getattr(self.config, 'HANDOFF_ROUND_THRESHOLD', 3)

    def get_or_create_ticket(self, session_id: int) -> SupportTicket:
        """
        Get existing ticket or create a new one for the session.

        Args:
            session_id: Conversation session ID

        Returns:
            SupportTicket instance
        """
        ticket = SupportTicket.query.filter_by(session_id=session_id).first()
        if not ticket:
            ticket = SupportTicket(session_id=session_id, status='open', round_count=0)
            db.session.add(ticket)
            db.session.commit()
            logger.info(f'Created new support ticket for session {session_id}')
        return ticket

    def get_ticket(self, session_id: int) -> Optional[SupportTicket]:
        """
        Get ticket by session ID.

        Args:
            session_id: Conversation session ID

        Returns:
            SupportTicket instance or None
        """
        return SupportTicket.query.filter_by(session_id=session_id).first()

    def get_ticket_status(self, session_id: int) -> Tuple[str, int]:
        """
        Get ticket status and round count.

        Args:
            session_id: Conversation session ID

        Returns:
            Tuple of (status, round_count)
        """
        ticket = self.get_ticket(session_id)
        if not ticket:
            # Auto-create ticket if not exists
            ticket = self.get_or_create_ticket(session_id)
        return ticket.status, ticket.round_count

    def increment_round(self, session_id: int) -> Tuple[int, bool]:
        """
        Increment conversation round count.

        Args:
            session_id: Conversation session ID

        Returns:
            Tuple of (new_round_count, should_show_handoff)
        """
        ticket = self.get_or_create_ticket(session_id)

        # Only count rounds for open tickets
        if ticket.status != 'open':
            return ticket.round_count, False

        ticket.increment_round()
        db.session.commit()

        should_show_handoff = ticket.round_count >= self.handoff_threshold
        logger.info(f'Incremented round count for session {session_id} to {ticket.round_count}, handoff={should_show_handoff}')

        return ticket.round_count, should_show_handoff

    def request_human_handoff(self, session_id: int) -> bool:
        """
        Mark ticket as pending human handoff.

        Args:
            session_id: Conversation session ID

        Returns:
            True if successful, False if ticket is not open
        """
        ticket = self.get_ticket(session_id)
        if not ticket:
            logger.warning(f'Cannot request handoff: no ticket for session {session_id}')
            return False

        if ticket.status != 'open':
            logger.warning(f'Cannot request handoff: ticket {ticket.id} is {ticket.status}')
            return False

        ticket.mark_pending_human()

        # Also update chat memory
        latest_memory = ChatMemory.query.filter_by(session_id=session_id).order_by(ChatMemory.created_at.desc()).first()
        if latest_memory:
            latest_memory.update_ticket_status('pending_human')

        db.session.commit()
        logger.info(f'Ticket {ticket.id} marked as pending human handoff')
        return True

    def close_ticket(self, session_id: int, closed_by: str, user_id: Optional[int] = None) -> bool:
        """
        Close a ticket.

        Args:
            session_id: Conversation session ID
            closed_by: Who closed the ticket ('user', 'tech_support')
            user_id: Optional user ID

        Returns:
            True if successful, False if ticket doesn't exist or is already closed
        """
        ticket = self.get_ticket(session_id)
        if not ticket:
            logger.warning(f'Cannot close: no ticket for session {session_id}')
            return False

        if ticket.is_closed():
            logger.warning(f'Cannot close: ticket {ticket.id} is already closed')
            return False

        ticket.close(closed_by, user_id)

        # Also update chat memory
        latest_memory = ChatMemory.query.filter_by(session_id=session_id).order_by(ChatMemory.created_at.desc()).first()
        if latest_memory:
            latest_memory.update_ticket_status('closed')

        db.session.commit()
        logger.info(f'Ticket {ticket.id} closed by {closed_by}')
        return True

    def should_show_handoff_button(self, session_id: int) -> bool:
        """
        Check if human handoff button should be shown.

        Args:
            session_id: Conversation session ID

        Returns:
            True if button should be shown
        """
        ticket = self.get_ticket(session_id)
        if not ticket:
            return False

        return ticket.is_open() and ticket.round_count >= self.handoff_threshold


# Singleton instance
ticket_service = TicketService()
