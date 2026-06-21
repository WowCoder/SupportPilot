"""
Unified JSON response helpers for SupportPilot API.

All /api/v1/ endpoints should use these helpers to ensure
consistent response format: { code, data, message }
"""
from flask import jsonify


def api_success(data=None, code=200, message='ok'):
    """
    Create a success JSON response.

    Args:
        data: Response payload (dict, list, or None)
        code: HTTP status code (default 200)
        message: Human-readable message

    Returns:
        Flask JSON response tuple
    """
    return jsonify({
        'code': code,
        'data': data,
        'message': message,
    }), code


def api_error(code=400, message='Bad request'):
    """
    Create an error JSON response.

    Args:
        code: HTTP status code (default 400)
        message: Human-readable error message

    Returns:
        Flask JSON response tuple
    """
    return jsonify({
        'code': code,
        'data': None,
        'message': message,
    }), code


def api_paginated(items, total, page=1, page_size=20):
    """
    Create a paginated success JSON response.

    Args:
        items: List of items for current page
        total: Total number of items across all pages
        page: Current page number
        page_size: Items per page

    Returns:
        Flask JSON response tuple
    """
    return jsonify({
        'code': 200,
        'data': {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
        },
        'message': 'ok',
    }), 200
