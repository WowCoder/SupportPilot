from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, current_app
from flask_login import current_user, login_user, logout_user, login_required
from app import db
from models import User, Conversation, Message, Document
import os
from werkzeug.utils import secure_filename
from rag.rag_utils import rag_utils
from api.qwen_api import qwen_api

main_bp = Blueprint('main', __name__)

# Authentication routes
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        # Validate username
        if len(username) < 3 or len(username) > 64:
            flash('Username must be between 3 and 64 characters')
            return redirect(url_for('register'))
        # Validate email
        if not email or '@' not in email:
            flash('Invalid email address')
            return redirect(url_for('register'))
        # Validate password strength
        is_valid, message = User.validate_password_strength(password)
        if not is_valid:
            flash(message)
            return redirect(url_for('register'))
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        # Create new user
        user = User(username=username, email=email, role='user')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful!')
        return redirect(url_for('login'))
    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main routes
@main_bp.route('/')
@login_required
def index():
    if current_user.role == 'tech_support':
        # Tech support dashboard
        conversations = Conversation.query.all()
        needs_attention = Conversation.query.filter_by(status='needs_attention').all()
        return render_template('tech_dashboard.html', conversations=conversations, needs_attention=needs_attention)
    else:
        # User dashboard
        conversations = current_user.conversations.order_by(Conversation.last_message_at.desc()).all()
        return render_template('user_dashboard.html', conversations=conversations)

# User routes
@main_bp.route('/conversation/new', methods=['POST'])
@login_required
def create_conversation():
    if current_user.role == 'user':
        conversation = Conversation(user_id=current_user.id)
        db.session.add(conversation)
        db.session.commit()
        return redirect(url_for('conversation', conversation_id=conversation.id))
    return redirect(url_for('index'))

@main_bp.route('/conversation/<int:conversation_id>')
@login_required
def conversation(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    # Check if user is the owner or tech support
    if conversation.user_id != current_user.id and current_user.role != 'tech_support':
        return redirect(url_for('index'))
    messages = conversation.messages.order_by(Message.timestamp).all()
    return render_template('conversation.html', conversation=conversation, messages=messages)

@main_bp.route('/conversation/<int:conversation_id>/send', methods=['POST'])
@login_required
def send_message(conversation_id):
    conversation = Conversation.query.get_or_404(conversation_id)
    if conversation.user_id != current_user.id and current_user.role != 'tech_support':
        return redirect(url_for('index'))
    
    content = request.form['content']
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
    
    # AI response if user is sending and not tech support
    if current_user.role == 'user' and conversation.status == 'active':
        # Use RAG to retrieve relevant information
        relevant_info = rag_utils.retrieve_relevant_info(content)
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
    
    return redirect(url_for('conversation', conversation_id=conversation_id))

# Tech support routes
@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if current_user.role != 'tech_support':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']:
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Process document for RAG
            if rag_utils.process_document(filepath):
                # Add to database
                document = Document(
                    filename=filename,
                    filepath=filepath,
                    uploaded_by=current_user.id
                )
                db.session.add(document)
                db.session.commit()
                flash('File uploaded and processed successfully')
            else:
                flash('File uploaded but processing failed')
            return redirect(url_for('upload'))
        else:
            flash('Allowed file types are txt, pdf, doc, docx')
    
    documents = Document.query.filter_by(uploaded_by=current_user.id).all()
    return render_template('upload.html', documents=documents)
