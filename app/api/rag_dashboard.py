"""API routes for RAG quality dashboard - feedback, logs, judge, stats."""
import json
import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask import g
from ..utils.auth import jwt_required
from sqlalchemy import func

from ..extensions import db
from ..models.rag_log import RagRetrievalLog, UserFeedback

logger = logging.getLogger(__name__)
rag_dash_bp = Blueprint('rag_dashboard_api', __name__, url_prefix='/api')


def _q(model):
    """Shortcut for db.session.query."""
    return db.session.query(model)


@rag_dash_bp.route('/feedback', methods=['POST'])
@jwt_required
def submit_feedback():
    """Submit user feedback (thumbs up/down) on an AI response."""
    data = request.get_json(silent=True) or {}

    message_id = data.get('message_id')
    conversation_id = data.get('conversation_id')
    feedback_type = data.get('type')

    if not message_id or not conversation_id or feedback_type not in ('positive', 'negative'):
        return jsonify({'success': False, 'message': '缺少必填字段'}), 400

    # Find latest retrieval log
    latest_log = _q(RagRetrievalLog).order_by(RagRetrievalLog.created_at.desc()).first()

    existing = _q(UserFeedback).filter_by(
        user_id=g.current_user.id, message_id=message_id
    ).first()

    updated = False
    if existing:
        existing.type = feedback_type
        if latest_log:
            existing.retrieval_log_id = latest_log.id
        updated = True
    else:
        feedback = UserFeedback(
            conversation_id=conversation_id,
            message_id=message_id,
            user_id=g.current_user.id,
            type=feedback_type,
            retrieval_log_id=latest_log.id if latest_log else None
        )
        db.session.add(feedback)

    db.session.commit()
    logger.info(f'Feedback: user={g.current_user.id} msg={message_id} type={feedback_type}')
    return jsonify({'success': True, 'updated': updated})


@rag_dash_bp.route('/rag-logs', methods=['GET'])
@jwt_required
def list_logs():
    """List retrieval logs with pagination and filters."""
    if g.current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    route_type = request.args.get('route_type', '')
    min_similarity = request.args.get('min_similarity', type=float)
    search = request.args.get('search', '')

    query = _q(RagRetrievalLog)

    if route_type:
        query = query.filter(RagRetrievalLog.route_type == route_type)
    if min_similarity is not None:
        query = query.filter(RagRetrievalLog.top1_similarity >= min_similarity)
    if search:
        query = query.filter(RagRetrievalLog.query.contains(search))

    # Manual pagination via offset/limit
    total = query.count()
    offset = (page - 1) * per_page
    logs = query.order_by(RagRetrievalLog.created_at.desc()).offset(offset).limit(per_page).all()

    items = []
    for log in logs:
        judge_score = None
        if log.judge_score:
            try:
                judge_score = json.loads(log.judge_score)
            except json.JSONDecodeError:
                pass

        items.append({
            'id': log.id,
            'query': log.query,
            'result_count': log.result_count,
            'top1_similarity': log.top1_similarity,
            'duration_ms': log.duration_ms,
            'route_type': log.route_type,
            'sub_query_count': log.sub_query_count or 0,
            'retry_count': log.retry_count or 0,
            'faithfulness_score': log.faithfulness_score,
            'judge_score': judge_score,
            'judge_reason': log.judge_reason,
            'created_at': log.created_at.isoformat() if log.created_at else None
        })

    # Compute stats
    avg_sim_row = _q(func.avg(RagRetrievalLog.top1_similarity)).scalar()
    avg_sim = round(float(avg_sim_row), 3) if avg_sim_row else 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = _q(RagRetrievalLog).filter(RagRetrievalLog.created_at >= today_start).count()

    judged = _q(RagRetrievalLog).filter(RagRetrievalLog.judge_score.isnot(None)).all()
    avg_judge = 0
    if judged:
        scores = []
        for log in judged:
            try:
                js = json.loads(log.judge_score)
                avg = (
                    js.get('relevance', 0)
                    + js.get('completeness', 0)
                    + js.get('noise', 0)
                ) / 3
                scores.append(avg)
            except (json.JSONDecodeError, TypeError):
                pass
        if scores:
            avg_judge = round(sum(scores) / len(scores), 2)

    total_fb = _q(UserFeedback).count()
    pos_fb = _q(UserFeedback).filter_by(type='positive').count()
    pos_rate = round(pos_fb / total_fb * 100, 1) if total_fb > 0 else 0

    pages = max(1, (total + per_page - 1) // per_page)

    return jsonify({
        'success': True,
        'items': items,
        'pagination': {
            'page': page,
            'pages': pages,
            'total': total,
            'has_prev': page > 1,
            'has_next': page < pages
        },
        'stats': {
            'total_queries': total,
            'avg_similarity': avg_sim,
            'avg_judge_score': avg_judge,
            'positive_rate': pos_rate,
            'today_queries': today_count
        }
    })


@rag_dash_bp.route('/rag-logs/<int:log_id>', methods=['GET'])
@jwt_required
def get_log_detail(log_id):
    """Get single log with full results_json and associated feedback."""
    if g.current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    log = _q(RagRetrievalLog).get_or_404(log_id)

    results = []
    if log.results_json:
        try:
            results = json.loads(log.results_json)
        except json.JSONDecodeError:
            pass

    judge_score = None
    if log.judge_score:
        try:
            judge_score = json.loads(log.judge_score)
        except json.JSONDecodeError:
            pass

    feedbacks = []
    for fb in _q(UserFeedback).filter_by(retrieval_log_id=log.id).all():
        feedbacks.append({
            'id': fb.id,
            'type': fb.type,
            'user_id': fb.user_id,
            'created_at': fb.created_at.isoformat() if fb.created_at else None
        })

    # Parse trace data
    trace = None
    if log.trace_json:
        try:
            trace = json.loads(log.trace_json)
        except json.JSONDecodeError:
            pass

    return jsonify({
        'success': True,
        'log': {
            'id': log.id,
            'query': log.query,
            'result_count': log.result_count,
            'top1_similarity': log.top1_similarity,
            'duration_ms': log.duration_ms,
            'route_type': log.route_type,
            'sub_query_count': log.sub_query_count or 0,
            'retry_count': log.retry_count or 0,
            'faithfulness_score': log.faithfulness_score,
            'results': results,
            'trace': trace,
            'judge_score': judge_score,
            'judge_reason': log.judge_reason,
            'feedbacks': feedbacks,
            'created_at': log.created_at.isoformat() if log.created_at else None
        }
    })


@rag_dash_bp.route('/rag-logs/<int:log_id>/judge', methods=['POST'])
@jwt_required
def trigger_judge(log_id):
    """Trigger LLM-as-Judge evaluation for a retrieval log."""
    if g.current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    log = _q(RagRetrievalLog).get_or_404(log_id)

    results = []
    if log.results_json:
        try:
            results = json.loads(log.results_json)
        except json.JSONDecodeError:
            pass

    if not results:
        return jsonify({'success': False, 'message': '无检索结果可评估'}), 400

    from evaluation.rag_evaluation import judge_retrieval
    result = judge_retrieval(log.query, results)

    if result and result.get('judge_score'):
        log.judge_score = json.dumps(result['judge_score'], ensure_ascii=False)
        log.judge_reason = result['judge_reason']
        db.session.commit()
        logger.info(f'Judge completed for log #{log.id}: {result["judge_score"]}')
        return jsonify({
            'success': True,
            'judge_score': result['judge_score'],
            'judge_reason': result['judge_reason']
        })
    else:
        return jsonify({
            'success': False,
            'message': result.get('judge_reason', '评估失败') if result else '评估失败'
        }), 500


@rag_dash_bp.route('/rag-logs/stats', methods=['GET'])
@jwt_required
def get_stats():
    """Get dashboard summary stats."""
    if g.current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    total = _q(RagRetrievalLog).count()

    avg_sim_row = _q(func.avg(RagRetrievalLog.top1_similarity)).scalar()
    avg_sim = round(float(avg_sim_row), 3) if avg_sim_row else 0

    judged = _q(RagRetrievalLog).filter(RagRetrievalLog.judge_score.isnot(None)).all()
    avg_judge = 0
    if judged:
        scores = []
        for log in judged:
            try:
                js = json.loads(log.judge_score)
                avg = (
                    js.get('relevance', 0)
                    + js.get('completeness', 0)
                    + js.get('noise', 0)
                ) / 3
                scores.append(avg)
            except (json.JSONDecodeError, TypeError):
                pass
        if scores:
            avg_judge = round(sum(scores) / len(scores), 2)

    total_fb = _q(UserFeedback).count()
    pos_fb = _q(UserFeedback).filter_by(type='positive').count()
    pos_rate = round(pos_fb / total_fb * 100, 1) if total_fb > 0 else 0

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = _q(RagRetrievalLog).filter(RagRetrievalLog.created_at >= today_start).count()

    return jsonify({
        'success': True,
        'stats': {
            'total_queries': total,
            'avg_similarity': avg_sim,
            'avg_judge_score': avg_judge,
            'positive_rate': pos_rate,
            'today_queries': today_count
        }
    })
