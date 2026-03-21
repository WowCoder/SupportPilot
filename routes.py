from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, current_app
from flask_login import current_user, login_user, logout_user, login_required
from extensions import db
from models import User, Conversation, Message, Document
import os
import logging
from werkzeug.utils import secure_filename
from rag.rag_utils import rag_utils
from api.qwen_api import qwen_api
from utils import sanitize_input

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

# Authentication routes
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # Validate username
        if len(username) < 3 or len(username) > 64:
            logger.warning(f'Registration failed: username {username} invalid length')
            flash('Username must be between 3 and 64 characters')
            return redirect(url_for('main.register'))
        # Validate email
        if not email or '@' not in email:
            logger.warning(f'Registration failed: invalid email {email}')
            flash('Invalid email address')
            return redirect(url_for('main.register'))
        # Validate password strength
        is_valid, message = User.validate_password_strength(password)
        if not is_valid:
            logger.warning(f'Registration failed: weak password for user {username}')
            flash(message)
            return redirect(url_for('main.register'))
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            logger.warning(f'Registration failed: username {username} already exists')
            flash('Username already exists')
            return redirect(url_for('main.register'))
        if User.query.filter_by(email=email).first():
            logger.warning(f'Registration failed: email {email} already exists')
            flash('Email already exists')
            return redirect(url_for('main.register'))
        # Create new user
        user = User(username=username, email=email, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        logger.info(f'User registered successfully: {username}')
        flash('Registration successful!')
        return redirect(url_for('main.login'))
    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            logger.info(f'User logged in: {username}')
            return redirect(url_for('main.index'))
        logger.warning(f'Login failed: invalid credentials for user {username}')
        flash('Invalid username or password')
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    username = current_user.username
    logout_user()
    logger.info(f'User logged out: {username}')
    return redirect(url_for('main.login'))

# Main routes
@main_bp.route('/')
@login_required
def index():
    if current_user.role == 'tech_support':
        # Tech support dashboard with pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20
        conversations = Conversation.query.order_by(Conversation.last_message_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        needs_attention = Conversation.query.filter_by(status='needs_attention').all()
        return render_template('tech_dashboard.html',
                               conversations=conversations.items,
                               needs_attention=needs_attention,
                               pagination=conversations)
    else:
        # User dashboard with pagination
        page = request.args.get('page', 1, type=int)
        per_page = 20
        conversations = current_user.conversations\
            .order_by(Conversation.last_message_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        return render_template('user_dashboard.html',
                               conversations=conversations.items,
                               pagination=conversations)

# User routes
@main_bp.route('/conversation/new', methods=['POST'])
@login_required
def create_conversation():
    if current_user.role == 'user':
        conversation = Conversation(user_id=current_user.id)
        db.session.add(conversation)
        db.session.commit()
        return redirect(url_for('main.conversation', conversation_id=conversation.id))
    return redirect(url_for('main.index'))

@main_bp.route('/conversation/<int:conversation_id>')
@login_required
def conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    # Check if user is the owner or tech support
    if conversation.user_id != current_user.id and current_user.role != 'tech_support':
        return redirect(url_for('main.index'))
    messages = conversation.messages.order_by(Message.timestamp).all()
    return render_template('conversation.html', conversation=conversation, messages=messages)

@main_bp.route('/conversation/<int:conversation_id>/send', methods=['POST'])
@login_required
def send_message(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id and current_user.role != 'tech_support':
        return redirect(url_for('main.index'))

    content = sanitize_input(request.form.get('content', ''))
    if not content:
        flash('Message content cannot be empty')
        return redirect(url_for('main.conversation', conversation_id=conversation_id))
    sender_type = 'user' if current_user.role == 'user' else 'tech_support'

    # Create user message
    message = Message(
        conversation_id=conversation_id,
        sender_type=sender_type,
        content=content
    )
    db.session.add(message)

    # Update conversation stats
    conversation.message_count += 1
    conversation.last_message_at = message.timestamp

    # Check if needs tech support intervention
    if conversation.message_count >= 3 and conversation.status == 'active':
        conversation.status = 'needs_attention'

    db.session.commit()

    # AI response if user is sending and conversation is active
    if current_user.role == 'user' and conversation.status == 'active':
        try:
            # Use RAG to retrieve relevant information
            relevant_info = rag_utils.retrieve_relevant_info(content, k=3)
            # Generate response using Qwen API
            ai_response = qwen_api.generate_response(content, relevant_info)
            ai_message = Message(
                conversation_id=conversation_id,
                sender_type='ai',
                content=ai_response
            )
            db.session.add(ai_message)
            conversation.message_count += 1
            conversation.last_message_at = ai_message.timestamp
            db.session.commit()
            logger.info(f'AI response generated for conversation {conversation_id}')
        except Exception as e:
            logger.error(f'Error generating AI response: {e}', exc_info=True)
            # Don't fail the entire request, just log the error

    return redirect(url_for('main.conversation', conversation_id=conversation_id))

# Tech support routes
@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized upload attempt by user: {current_user.username}')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if 'file' not in request.files:
            logger.warning('Upload failed: no file part')
            if is_ajax:
                return jsonify({'success': False, 'message': 'No file part'})
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            logger.warning('Upload failed: no selected file')
            if is_ajax:
                return jsonify({'success': False, 'message': 'No selected file'})
            flash('No selected file')
            return redirect(request.url)

        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']:
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                logger.info(f'File uploaded: {filename} by user {current_user.username}')

                # Get chunking parameters from request (with defaults)
                chunk_size = request.form.get('chunk_size', 1000, type=int)
                chunk_overlap = request.form.get('chunk_overlap', 200, type=int)

                # Process document for RAG
                result = rag_utils.process_document(filepath, chunk_size, chunk_overlap)

                if result.get('success'):
                    # Add to database
                    document = Document(
                        filename=filename,
                        filepath=filepath,
                        uploaded_by=current_user.id
                    )
                    db.session.add(document)
                    db.session.commit()
                    logger.info(f'Document processed successfully: {filename}')

                    chunks_added = result.get('chunks_added', 0)
                    chunks_total = result.get('chunks_total', 0)
                    is_duplicate = result.get('is_duplicate', False)

                    if is_ajax:
                        return jsonify({
                            'success': True,
                            'message': f'文件 "{filename}" 上传并处理成功',
                            'chunks_added': chunks_added,
                            'chunks_total': chunks_total,
                            'is_duplicate': is_duplicate
                        })
                    flash(f'File uploaded and processed successfully ({chunks_added} chunks added)')
                    return redirect(url_for('main.upload'))
                else:
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f'Document processing failed: {filename} - {error_msg}')
                    if is_ajax:
                        return jsonify({'success': False, 'message': f'处理失败：{error_msg}'}), 500
                    flash(f'File uploaded but processing failed: {error_msg}')
                    return redirect(url_for('main.upload'))

            except Exception as e:
                logger.error(f'Upload error: {str(e)}', exc_info=True)
                if is_ajax:
                    return jsonify({'success': False, 'message': str(e)}), 500
                flash('An error occurred during file upload')
                return redirect(url_for('main.upload'))
        else:
            logger.warning(f'Upload failed: invalid file type {file.filename}')
            if is_ajax:
                return jsonify({'success': False, 'message': 'Invalid file type'}), 400
            flash('Allowed file types are txt, pdf, doc, docx')
            return redirect(request.url)

    # GET request - show documents with pagination
    page = request.args.get('page', 1, type=int)
    per_page = 20
    documents = Document.query.filter_by(uploaded_by=current_user.id)\
        .order_by(Document.uploaded_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
    return render_template('upload.html', documents=documents.items, pagination=documents)


# Conversation management routes
@main_bp.route('/conversation/<int:conversation_id>/close', methods=['POST'])
@login_required
def close_conversation(conversation_id):
    """Close a conversation (tech support only)"""
    conversation = Conversation.query.get_or_404(conversation_id)

    # Only tech support can close conversations
    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized close attempt by user {current_user.username}')
        flash('Only tech support can close conversations')
        return redirect(url_for('main.conversation', conversation_id=conversation_id))

    conversation.status = 'closed'
    db.session.commit()
    logger.info(f'Conversation {conversation_id} closed by {current_user.username}')
    flash('Conversation closed successfully')
    return redirect(url_for('main.index'))


@main_bp.route('/conversation/<int:conversation_id>/reopen', methods=['POST'])
@login_required
def reopen_conversation(conversation_id):
    """Reopen a closed conversation (tech support only)"""
    conversation = Conversation.query.get_or_404(conversation_id)

    # Only tech support can reopen conversations
    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized reopen attempt by user {current_user.username}')
        flash('Only tech support can reopen conversations')
        return redirect(url_for('main.conversation', conversation_id=conversation_id))

    conversation.status = 'active'
    conversation.message_count = 0  # Reset message count
    db.session.commit()
    logger.info(f'Conversation {conversation_id} reopened by {current_user.username}')
    flash('Conversation reopened successfully')
    return redirect(url_for('main.conversation', conversation_id=conversation_id))


@main_bp.route('/conversation/<int:conversation_id>/mark-attention', methods=['POST'])
@login_required
def mark_conversation_attention(conversation_id):
    """Mark a conversation as needs attention (tech support only)"""
    conversation = Conversation.query.get_or_404(conversation_id)

    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized mark attempt by user {current_user.username}')
        flash('Permission denied')
        return redirect(url_for('main.conversation', conversation_id=conversation_id))

    conversation.status = 'needs_attention'
    db.session.commit()
    logger.info(f'Conversation {conversation_id} marked as needs_attention by {current_user.username}')
    flash('Conversation marked for attention')
    return redirect(url_for('main.conversation', conversation_id=conversation_id))


# Document management routes
@main_bp.route('/document/<int:document_id>/delete', methods=['POST'])
@login_required
def delete_document(document_id):
    """Delete a document (tech support only)"""
    if current_user.role != 'tech_support':
        logger.warning(f'Unauthorized delete attempt by user {current_user.username}')
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    document = Document.query.get_or_404(document_id)

    # Only allow deleting own documents
    if document.uploaded_by != current_user.id:
        logger.warning(f'User {current_user.username} tried to delete document owned by user {document.uploaded_by}')
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    try:
        filename = document.filename
        filepath = document.filepath

        # Delete from Chroma vector database
        rag_utils.delete_documents_by_source(filename)

        # Delete physical file
        if os.path.exists(filepath):
            os.remove(filepath)

        # Delete from database
        db.session.delete(document)
        db.session.commit()

        logger.info(f'Document deleted: {filename} by {current_user.username}')
        return jsonify({'success': True, 'message': f'Document "{filename}" deleted successfully'})

    except Exception as e:
        logger.error(f'Error deleting document {document_id}: {e}', exc_info=True)
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@main_bp.route('/api/document/count', methods=['GET'])
@login_required
def get_document_count():
    """Get total document count in RAG system"""
    try:
        count = rag_utils.get_document_count()
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f'Error getting document count: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@main_bp.route('/api/test-query', methods=['POST'])
@login_required
def test_query():
    """Test RAG retrieval with a query"""
    if current_user.role != 'tech_support':
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    data = request.get_json()
    query = data.get('query', '')
    k = data.get('k', 3)
    similarity_threshold = data.get('similarity_threshold', 0.1)

    if not query:
        return jsonify({'success': False, 'message': 'Query is required'}), 400

    try:
        results = rag_utils.retrieve_relevant_info(query, k=k, similarity_threshold=similarity_threshold)
        return jsonify({
            'success': True,
            'results': [
                {
                    'content': r['content'],
                    'similarity': r['similarity'],
                    'source': r['source']
                }
                for r in results
            ]
        })
    except Exception as e:
        logger.error(f'Error testing query: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
