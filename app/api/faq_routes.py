"""
FAQ API routes for SupportPilot

Handles FAQ operations: generate, review, confirm, reject, CRUD.
"""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
import logging

from ..extensions import db
from ..services.faq_review_service import faq_review_service
from ..services.faq_management_service import faq_management_service

logger = logging.getLogger(__name__)

faq_bp = Blueprint('faq', __name__, url_prefix='/api/faq')


# ===== Review Workflow APIs =====

@faq_bp.route('/generate', methods=['POST'])
@login_required
def generate_faq():
    """
    Generate FAQ draft from conversation.

    Request JSON:
        - session_id: Conversation session ID

    Returns:
        JSON with FAQ draft
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'success': False, 'message': '缺少 session_id'}), 400

    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': '仅技术支持可生成 FAQ'}), 403

    try:
        faq = faq_review_service.generate_faq_draft(session_id, current_user.id)

        if faq:
            return jsonify({
                'success': True,
                'faq': {
                    'id': faq.id,
                    'question': faq.question,
                    'answer': faq.answer,
                    'category': faq.category,
                    'status': faq.status
                }
            })
        else:
            return jsonify({'success': False, 'message': '生成 FAQ 失败'}), 500

    except Exception as e:
        logger.error(f'Error generating FAQ: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@faq_bp.route('/<int:faq_id>/update', methods=['POST'])
@login_required
def update_faq_draft(faq_id):
    """
    Update FAQ draft with edits.

    Request JSON:
        - question: Updated question
        - answer: Updated answer
        - category: Updated category
        - change_reason: Optional reason for change

    Returns:
        JSON with success status
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': '仅技术支持可编辑 FAQ'}), 403

    data = request.get_json(silent=True) or {}

    try:
        success = faq_review_service.update_faq_draft(
            faq_id=faq_id,
            question=data.get('question', ''),
            answer=data.get('answer', ''),
            category=data.get('category', ''),
            user_id=current_user.id,
            change_reason=data.get('change_reason')
        )

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': '更新失败'}), 400

    except Exception as e:
        logger.error(f'Error updating FAQ: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@faq_bp.route('/<int:faq_id>/confirm', methods=['POST'])
@login_required
def confirm_faq(faq_id):
    """
    Confirm FAQ and sync to ChromaDB.

    Returns:
        JSON with success status and progress
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': '仅技术支持可确认 FAQ'}), 403

    try:
        # Step 1: Mark as processing
        faq = faq_review_service.get_faq_by_id(faq_id)
        if not faq:
            return jsonify({'success': False, 'message': 'FAQ 不存在'}), 404

        # Step 2: Sync to ChromaDB with progress
        from rag.faq_vector_sync import sync_faq_to_chroma

        # Update progress: syncing
        faq.sync_progress = 50
        db.session.commit()

        chroma_doc_ids = sync_faq_to_chroma(faq)
        if not chroma_doc_ids:
            faq.sync_progress = 0
            faq.sync_error = '向量化失败'
            db.session.commit()
            logger.error(f'Failed to sync FAQ {faq_id} to ChromaDB')
            return jsonify({'success': False, 'message': '向量化失败', 'progress': 50}), 500

        # Update progress: complete
        faq.sync_progress = 100
        faq.mark_as_confirmed(current_user.id, chroma_doc_ids)

        # Add final version record
        version = faq.add_version(current_user.id, 'Confirmed and synced to ChromaDB')
        db.session.add(version)

        db.session.commit()
        logger.info(f'FAQ {faq_id} confirmed and synced to ChromaDB')

        return jsonify({
            'success': True,
            'message': 'FAQ 已确认并添加到知识库',
            'progress': 100
        })

    except Exception as e:
        logger.error(f'Error confirming FAQ: {e}', exc_info=True)
        if faq:
            faq.sync_progress = 0
            faq.sync_error = str(e)
            db.session.commit()
        return jsonify({'success': False, 'error': str(e), 'progress': 0}), 500


@faq_bp.route('/<int:faq_id>/reject', methods=['POST'])
@login_required
def reject_faq(faq_id):
    """
    Reject FAQ draft.

    Request JSON:
        - reason: Optional rejection reason

    Returns:
        JSON with success status
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': '仅技术支持可拒绝 FAQ'}), 403

    data = request.get_json(silent=True) or {}

    try:
        success = faq_review_service.reject_faq(
            faq_id=faq_id,
            user_id=current_user.id,
            reason=data.get('reason')
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'FAQ 已拒绝'
            })
        else:
            return jsonify({'success': False, 'message': '拒绝失败'}), 400

    except Exception as e:
        logger.error(f'Error rejecting FAQ: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


# ===== Management APIs =====

@faq_bp.route('', methods=['GET'])
@login_required
def list_faqs():
    """
    List FAQ entries with optional filtering.

    Query params:
        - status: Filter by status
        - category: Filter by category
        - search: Search keyword
        - page: Page number (default 1)
        - per_page: Items per page (default 20)

    Returns:
        JSON with FAQ list and pagination
    """
    try:
        result = faq_management_service.get_all_faqs(
            status=request.args.get('status'),
            category=request.args.get('category'),
            search=request.args.get('search'),
            page=request.args.get('page', 1, type=int),
            per_page=request.args.get('per_page', 20, type=int)
        )

        return jsonify({
            'success': True,
            'items': [
                {
                    'id': faq.id,
                    'question': faq.question,
                    'answer': faq.answer,
                    'category': faq.category,
                    'status': faq.status,
                    'created_at': faq.created_at.isoformat() if faq.created_at else None,
                    'creator': faq.creator.username if faq.creator else None
                }
                for faq in result['items']
            ],
            'pagination': result['pagination']
        })

    except Exception as e:
        logger.error(f'Error listing FAQs: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@faq_bp.route('', methods=['POST'])
@login_required
def create_faq():
    """
    Create a new FAQ entry.

    Request JSON:
        - question: FAQ question
        - answer: FAQ answer
        - category: FAQ category
        - status: Initial status ('draft' or 'confirmed'), default 'draft'

    Returns:
        JSON with created FAQ
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': '仅技术支持可创建 FAQ'}), 403

    data = request.get_json(silent=True) or {}

    if not data.get('question') or not data.get('answer'):
        return jsonify({'success': False, 'message': '问题和答案为必填项'}), 400

    try:
        faq = faq_management_service.create_faq(
            question=data.get('question', ''),
            answer=data.get('answer', ''),
            category=data.get('category', ''),
            user_id=current_user.id,
            status=data.get('status', 'draft')
        )

        if faq:
            return jsonify({
                'success': True,
                'faq': {
                    'id': faq.id,
                    'question': faq.question,
                    'answer': faq.answer,
                    'category': faq.category,
                    'status': faq.status
                }
            }, status=201)
        else:
            return jsonify({'success': False, 'message': '创建失败'}), 500

    except Exception as e:
        logger.error(f'Error creating FAQ: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@faq_bp.route('/<int:faq_id>', methods=['GET'])
@login_required
def get_faq(faq_id):
    """
    Get a single FAQ entry by ID.

    Returns:
        JSON with FAQ details
    """
    try:
        faq = faq_management_service.get_faq_by_id(faq_id)
        if not faq:
            return jsonify({'success': False, 'message': 'FAQ 不存在'}), 404

        return jsonify({
            'success': True,
            'faq': {
                'id': faq.id,
                'question': faq.question,
                'answer': faq.answer,
                'category': faq.category,
                'status': faq.status,
                'sync_progress': faq.sync_progress,
                'created_at': faq.created_at.isoformat() if faq.created_at else None,
                'creator': faq.creator.username if faq.creator else None
            }
        })

    except Exception as e:
        logger.error(f'Error getting FAQ: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@faq_bp.route('/<int:faq_id>', methods=['PUT'])
@login_required
def update_faq(faq_id):
    """
    Update an FAQ entry.

    Request JSON:
        - question: Updated question
        - answer: Updated answer
        - category: Updated category
        - change_reason: Reason for change

    Returns:
        JSON with success status
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': '仅技术支持可编辑 FAQ'}), 403

    data = request.get_json(silent=True) or {}

    try:
        success = faq_management_service.update_faq(
            faq_id=faq_id,
            question=data.get('question'),
            answer=data.get('answer'),
            category=data.get('category'),
            user_id=current_user.id,
            change_reason=data.get('change_reason')
        )

        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': '更新失败'}), 400

    except Exception as e:
        logger.error(f'Error updating FAQ: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@faq_bp.route('/<int:faq_id>', methods=['DELETE'])
@login_required
def delete_faq(faq_id):
    """
    Delete an FAQ entry (soft delete).

    Returns:
        JSON with success status
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': '仅技术支持可删除 FAQ'}), 403

    try:
        success = faq_management_service.delete_faq(faq_id)

        if success:
            return jsonify({
                'success': True,
                'message': 'FAQ 已删除'
            })
        else:
            return jsonify({'success': False, 'message': '删除失败'}), 400

    except Exception as e:
        logger.error(f'Error deleting FAQ: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@faq_bp.route('/<int:faq_id>/versions', methods=['GET'])
@login_required
def get_faq_versions(faq_id):
    """
    Get version history for an FAQ entry.

    Returns:
        JSON with version list
    """
    try:
        versions = faq_management_service.get_version_history(faq_id)

        return jsonify({
            'success': True,
            'versions': [
                {
                    'id': v.id,
                    'question': v.question,
                    'answer': v.answer,
                    'change_reason': v.change_reason,
                    'changed_by': v.changed_by,
                    'created_at': v.created_at.isoformat() if v.created_at else None
                }
                for v in versions
            ]
        })

    except Exception as e:
        logger.error(f'Error getting FAQ versions: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@faq_bp.route('/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_faqs():
    """
    Delete multiple FAQ entries.

    Request JSON:
        - faq_ids: List of FAQ IDs to delete

    Returns:
        JSON with success/failed counts
    """
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': '仅技术支持可批量删除 FAQ'}), 403

    data = request.get_json(silent=True) or {}
    faq_ids = data.get('faq_ids', [])

    if not faq_ids:
        return jsonify({'success': False, 'message': '未选择要删除的 FAQ'}), 400

    try:
        result = faq_management_service.bulk_delete(faq_ids)

        return jsonify({
            'success': True,
            'result': result,
            'message': f'成功删除 {result["success"]} 个 FAQ，失败 {result["failed"]} 个'
        })

    except Exception as e:
        logger.error(f'Error bulk deleting FAQs: {e}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
