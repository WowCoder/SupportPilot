"""
FAQ API v1 — CRUD endpoints for Vue SPA frontend.
"""
import logging
from flask import Blueprint, request, g
from ...extensions import db
from ...models import FAQEntry
from ...utils.auth import jwt_required
from ...utils.response import api_success, api_error

logger = logging.getLogger(__name__)

faq_v1_bp = Blueprint('faq_v1', __name__, url_prefix='/api/v1/faq')


def _faq_to_dict(faq):
    return {
        'id': faq.id,
        'question': faq.question,
        'answer': faq.answer,
        'category': faq.category or '',
        'status': faq.status,
        'source_session_id': faq.source_session_id,
        'created_at': faq.created_at.isoformat(),
        'updated_at': faq.updated_at.isoformat() if faq.updated_at else None,
    }


@faq_v1_bp.route('/entries', methods=['GET'])
@jwt_required
def list_entries():
    """List FAQ entries with optional filters."""
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    page = request.args.get('page', type=int, default=1)
    page_size = request.args.get('page_size', type=int, default=20)
    status = request.args.get('status')
    category = request.args.get('category')
    search = request.args.get('search')

    query = FAQEntry.query

    if status:
        query = query.filter_by(status=status)
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(
            db.or_(
                FAQEntry.question.ilike(f'%{search}%'),
                FAQEntry.answer.ilike(f'%{search}%'),
            )
        )

    query = query.order_by(FAQEntry.created_at.desc())
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)

    # Also return stats if requested
    stats = None
    if request.args.get('stats') == 'true':
        stats = {
            'total': FAQEntry.query.count(),
            'confirmed': FAQEntry.query.filter_by(status='confirmed').count(),
            'pending': FAQEntry.query.filter_by(status='pending_review').count(),
            'draft': FAQEntry.query.filter_by(status='draft').count(),
        }

    return api_success({
        'items': [_faq_to_dict(e) for e in pagination.items],
        'total': pagination.total,
        'page': page,
        'page_size': page_size,
        'stats': stats,
    })


@faq_v1_bp.route('/entries', methods=['POST'])
@jwt_required
def create_entry():
    """Create a new FAQ entry (draft)."""
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    data = request.get_json(silent=True) or {}
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    category = data.get('category', '').strip()

    if not question or not answer:
        return api_error(400, 'Question and answer are required')

    entry = FAQEntry(
        question=question,
        answer=answer,
        category=category or None,
        status='draft',
    )
    db.session.add(entry)
    db.session.commit()

    logger.info(f'FAQ entry {entry.id} created by {user.username}')
    return api_success(_faq_to_dict(entry), code=201)


@faq_v1_bp.route('/entries/<int:entry_id>', methods=['PUT'])
@jwt_required
def update_entry(entry_id):
    """Update an existing FAQ entry."""
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    entry = FAQEntry.query.get_or_404(entry_id)
    data = request.get_json(silent=True) or {}

    if 'question' in data:
        entry.question = data['question'].strip()
    if 'answer' in data:
        entry.answer = data['answer'].strip()
    if 'category' in data:
        entry.category = data['category'].strip() or None
    if 'status' in data:
        new_status = data['status']
        if new_status in ('confirmed', 'rejected', 'draft', 'pending_review'):
            entry.status = new_status

    db.session.commit()
    logger.info(f'FAQ entry {entry_id} updated by {user.username}')
    return api_success(_faq_to_dict(entry))


@faq_v1_bp.route('/entries/<int:entry_id>', methods=['DELETE'])
@jwt_required
def delete_entry(entry_id):
    """Delete a FAQ entry."""
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    entry = FAQEntry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()

    logger.info(f'FAQ entry {entry_id} deleted by {user.username}')
    return api_success(message='FAQ deleted successfully')


@faq_v1_bp.route('/entries/bulk-delete', methods=['POST'])
@jwt_required
def bulk_delete():
    """Delete multiple FAQ entries."""
    user = g.current_user
    if user.role != 'tech_support':
        return api_error(403, 'Permission denied')

    data = request.get_json(silent=True) or {}
    entry_ids = data.get('ids', [])

    if not entry_ids:
        return api_error(400, 'No entry IDs provided')

    count = FAQEntry.query.filter(FAQEntry.id.in_(entry_ids)).delete(synchronize_session='fetch')
    db.session.commit()

    logger.info(f'{count} FAQ entries bulk-deleted by {user.username}')
    return api_success({'deleted': count})


@faq_v1_bp.route('/categories', methods=['GET'])
@jwt_required
def list_categories():
    """List distinct FAQ categories."""
    from sqlalchemy import distinct
    categories = (
        db.session.query(distinct(FAQEntry.category))
        .filter(FAQEntry.category.isnot(None))
        .order_by(FAQEntry.category)
        .all()
    )
    return api_success([c[0] for c in categories])
