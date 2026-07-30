from app import app, login_manager, db
from sqlalchemy import text
from flask import request, jsonify
import re
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, Post, Doctor, Question, Answer
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity


@app.route('/')
def index():
    return ""

@app.route('/db')
def db():
    try:
        db.session.execute(text("SELECT 1"))
        return {"db": "ok"}, 200
    except Exception as e:
        return {"db": "error", "details": str(e)}, 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return {"return": "Missing username or password"}

    user = User.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return {"return": "Invalid username or password"}

    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        "message": "Log in success",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
        }
    }), 200

@app.route('/api/register', methods=['POST', 'GET'])
def register():
    data = request.get_json() or {}
    errors = []
    
        
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirm_pass") or ""

    if not (3 <= len(username) <= 80):
        errors.append("Username must be between 3 and 80 characters")
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        errors.append("Username must be alphanumeric")
    if not (3 <= len(password) <= 80):
        errors.append("Password must be between 3 and 80 characters")
    if password != confirm:
        errors.append("Passwords must match")
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        errors.append("Invalid email address")
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        pw_hash = generate_password_hash(password)
        user = User(username=username, email=email, password_hash=pw_hash)
        db.session.add(user)
        db.session.commit()
        return jsonify({"success": True}), 200
    except IntegrityError:
        db.session.rollback()
        errors.append("Username or email already exists")
        return jsonify({"errors": errors}), 400

    return ""

@login_manager.user_loader
def load_user(user_id):
    return None

@app.route('/api/feed/home', methods=['GET'])
def home_feed():
    """
    Home feed: combined posts and questions.
    Query: ?type=all|posts|questions&page=1&per_page=20
    """
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)
    content_type = request.args.get('content_type', 'all')
    results = []

    # Posts
    if content_type in ['all', 'posts']:
    posts = Post.query.order_by(Post.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    for post in posts.items:
        if post.doctor_id and post.doctor_author:
            author = {
                'id': post.doctor_author.id,
                'username': post.doctor_author.username,
                'is doctor': True,
                'is verified': post.doctor_author.is_verified,
                'avatar_url': post.doctor_author.avatar_url,
                'specialization': post.doctor_author.specialization
            }
        elif post.user_id and post.user_author:
            author = {
                'id': post.user_author.id,
                'username': post.user_author.username,
                'is doctor': False,
                'is verified': False,
                'avatar_url': post.user_author.avatar_url,
                'specialization': None
            }
        else:
            author = {'username': post.author, 'is doctor': False}

        results.append({
            'id': post.id,
            'type': 'post',
            'title': post.title,
            'content': post.content,
            'image_url': post.image_url,
            'created_at': post.created_at.isoformat() if post.created_at else None,
            'likes_count': post.likes_count or 0,
            'author': author
        })

# Questions
if content_type in ['all', 'questions']:
    questions = Question.query.order_by(Question.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    for q in questions.items:
        if q.is_anonymous:
            author = None
        elif q.doctor_id and q.doctor_author:
            author = {
                'id': q.doctor_author.id,
                'username': q.doctor_author.username,
                'is doctor': True,
                'is verified': q.doctor_author.is_verified,
                'avatar_url': q.doctor_author.avatar_url,
                'specialization': q.doctor_author.specialization
            }
        elif q.user_id and q.user_author:  
            author = {
                'id': q.user_author.id,
                'username': q.user_author.username,
                'is doctor': False,
                'is verified': False,
                'avatar_url': q.user_author.avatar_url,
                'specialization': None
            }
        else:
            author = {'username': q.author, 'is doctor': False}

# Top 3 Answers
        top_answers = q.answers.order_by(Answer.created_at.asc()).limit(3).all()
        answers_preview = []
        for ans in top_answers:
            if ans.doctor_id and ans.doctor_author:
                ans_author = {
                    'id': ans.doctor_author.id,
                    'username': ans.doctor_author.username,
                    'is doctor': True,
                    'is verified': ans.doctor_author.is_verified,
                   }
            elif ans.user_id and ans.user_author:
                ans_author = {
                    'id': ans.user_author.id,
                    'username': ans.user_author.username,
                    'is doctor': False,
                    'is verified': False,
                }
            else:
                ans_author = {'username': ans.author, 'is doctor': False}

            answers_preview.append({
                'id': ans.id,
                'content': ans.content[:200] + '...' if len(ans.content) > 200 else ans.content,
                'is_doctor_answer': ans.is_doctor_answer,
                'created_at': ans.created_at.isoformat() if ans.created_at else None,
                'author': ans_author
            })
        results.append({
            'id': q.id,
            'type': 'question',
            'title': q.title,
            'content': q.content,
            'is_anonymous': q.is_anonymous or False,
            'is_resolved': q.is_resolved or False,
            'created_at': q.created_at.isoformat() if q.created_at else None,
            'answer_count': q.answers.count(),
            'author': author,
            'top_answers': answers_preview
        })

# Sort combined feed by date
if content_type == 'all':
    results.sort(key=lambda x: x['created_at'] or '', reverse=True)
    start = (page - 1) * per_page
    end = start + per_page
    results = results[start:end]

return jsonify({'page': page, 'per_page': per_page, 'results': results}), 200


@app.route('api/feed/questions/<int:question_id>/answers', methods=['GET'])
def get_question_answers(question_id):
    """Get all answers for a specific question."""
    question = Question.query.get_or_404(question_id)
    page = request.args.get('page', 1, type=int)
    answers = question.answers.order_by(Answer.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    answers_data = []
    for ans in answers.items:
        if ans.doctor_id and ans.doctor_author:
            author = {
                'id': ans.doctor_author.id,
                'username': ans.doctor_author.username,
                'is doctor': True,
                'is verified': ans.doctor_author.is_verified,
                'avatar_url': ans.doctor_author.avatar_url,
                'specialization': ans.doctor_author.specialization
            }
        elif ans.user_id and ans.user_author:
            author = {
                'id': ans.user_author.id,
                'username': ans.user_author.username,
                'is doctor': False,
                'is verified': False,
                'avatar_url': ans.user_author.avatar_url,
                'specialization': None
            }
        else:  
            author = {'username': ans.author, 'is doctor': False}
        answers_data.append({
            'id': ans.id,
            'content': ans.content,
            'is_doctor_answer': ans.is_doctor_answer,
            'likes_count': ans.likes_count or 0,
            'created_at': ans.created_at.isoformat() if ans.created_at else None,
            'author': author
        })

        return jsonify({
            'question_id': question.id,
            'question_title': question.title,
            'question_content': question.content,
            'is_anonymous': question.is_anonymous or False,
            'is_resolved': question.is_resolved or False,
            'answers': answers_data,
            'page': page,
            'total_pages': answers.pages,
        }), 200