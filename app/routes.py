import re
import os

from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, Post, Doctor, Question, Answer
from werkzeug.utils import secure_filename

from app import app, db
from app.models import User, Post, Doctor, Question, Answer, Favorite


@app.route("/")
def index():
    return jsonify({"status": "DocTweet API is active"}), 200


@app.route('/db')
def db_check():
    try:
        db.session.execute(text("SELECT 1"))
        return {"db": "ok"}, 200
    except Exception as e:
        return {"db": "error", "details": str(e)}, 500


@app.route("/api/login", methods=["POST", "OPTIONS"])
@app.route("/api/auth/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    data = request.get_json() or {}
    identifier = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "Missing username or password"}), 400

    # Search in User table first (by username or email)
    account = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    role = "member"

    # If not found in User, search in Doctor table
    if not account:
        account = Doctor.query.filter((Doctor.username == identifier) | (Doctor.email == identifier)).first()
        role = "doctor"

    if not account or not check_password_hash(account.password_hash, password):
        return jsonify({"error": "Invalid username or password"}), 401

    access_token = create_access_token(
        identity=str(account.id),
        additional_claims={"role": getattr(account, "role", role)}
    )

    return jsonify({
        "message": "Log in success",
        "access_token": access_token,
        "user": {
            "id": account.id,
            "username": account.username,
            "email": account.email,
            "role": getattr(account, "role", role),
        }
    }), 200


@app.route("/api/auth/register/doctor", methods=["POST", "GET"])
def register_doctor():
    if request.method == "GET":
        return jsonify({"msg": "Use POST to submit doctor registration"}), 200

    data = request.get_json() or {}
    errors = []

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirm_pass") or ""
    institution = (data.get("institution") or "").strip()
    specialization = (data.get("specialization") or "").strip()

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
    if not institution:
        errors.append("Institution is required")
    if errors:
        return jsonify({"errors": errors}), 400

    try:
        pw_hash = generate_password_hash(password)
        doctor = Doctor(
            username=username,
            email=email,
            password_hash=pw_hash,
            institution=institution,
            specialization=specialization,
        )
        db.session.add(doctor)
        db.session.commit()
        return jsonify({"success": True, "doctor": doctor.to_dict()}), 200
    except IntegrityError:
        db.session.rollback()
        errors.append("Username or email already exists")
        return jsonify({"errors": errors}), 400


@app.route("/api/auth/register/member", methods=["POST", "GET"])
def register_member():
    if request.method == "GET":
        return jsonify({"msg": "Use POST to submit member registration"}), 200

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
        user = User(
            username=username,
            email=email,
            password_hash=pw_hash,
            role="member",
        )
        db.session.add(user)
        db.session.commit()
        return jsonify({"success": True, "user": user.to_dict()}), 200
    except IntegrityError:
        db.session.rollback()
        errors.append("Username or email already exists")
        return jsonify({"errors": errors}), 400


@app.route("/api/getposts", methods=["GET"])
def get_posts():
    posts = Post.query.all()
    posts_data = [
        {
            "id": post.id,
            "title": getattr(post, "title", ""),
            "content": post.content,
            "author": getattr(post, "author", ""),
            "image_url": getattr(post, "image_url", None),
            "likes_count": getattr(post, "likes_count", 0),
            "created_at": post.created_at.isoformat() if getattr(post, "created_at", None) else None,
        }
        for post in posts
    ]
    return jsonify(posts_data), 200


@app.route("/api/getquestions", methods=["GET"])
def get_questions():
    questions = Question.query.all()
    questions_data = [
        {
            "id": q.id,
            "title": getattr(q, "title", ""),
            "content": getattr(q, "content", getattr(q, "question", "")),
            "author": getattr(q, "author", ""),
            "is_anonymous": getattr(q, "is_anonymous", False),
            "is_resolved": getattr(q, "is_resolved", False),
            "created_at": q.created_at.isoformat() if getattr(q, "created_at", None) else None,
        }
        for q in questions
    ]
    return jsonify(questions_data), 200


@app.route("/api/questions", methods=["POST", "OPTIONS"])
@jwt_required(optional=True)
def create_question():
    if request.method == "OPTIONS":
        return jsonify({"status": "OK"}), 200

    current_user_id = get_jwt_identity()
    if not current_user_id:
        return jsonify({"error": "Unauthorized: Token missing or invalid"}), 401

    data = request.get_json() or {}
    title = data.get("title", "").strip()
    content = (data.get("content") or data.get("question") or "").strip()
    is_anonymous = data.get("is_anonymous", False)

    if not content or not title:
        return jsonify({"error": "Title and question content are required"}), 400

    # Fetch user or doctor details for the author field
    user_id = int(current_user_id)
    account = User.query.get(user_id)
    doc_id = None
    
    if account:
        author_name = "Anonymous" if is_anonymous else account.username
    else:
        account = Doctor.query.get(user_id)
        if account:
            doc_id = account.id
            user_id = None
            author_name = f"Dr. {account.username}"
        else:
            return jsonify({"error": "User account not found"}), 404

    new_question = Question(
        title=title,
        content=content,
        author=author_name,
        user_id=user_id,
        doctor_id=doc_id,
        is_anonymous=is_anonymous
    )
    db.session.add(new_question)
    db.session.commit()

    return jsonify({
        "message": "Question posted successfully",
        "id": new_question.id
    }), 201


@app.route("/api/doctors", methods=["GET"])
def get_doctors():
    doctors = Doctor.query.all()
    doctors_data = [
        {
            "id": doctor.id,
            "username": doctor.username,
            "email": doctor.email,
            "institution": getattr(doctor, "institution", ""),
            "specialization": getattr(doctor, "specialization", ""),
            "avatar_url": getattr(doctor, "avatar_url", None),
            "is_verified": getattr(doctor, "is_verified", False),
            "created_at": doctor.created_at.isoformat() if getattr(doctor, "created_at", None) else None,
        }
        for doctor in doctors
    ]
    return jsonify(doctors_data), 200


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        upload_dir = app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, filename))
        return jsonify({"success": True, "filename": filename}), 200
    return jsonify({"error": "Upload failed"}), 400


@app.route('/api/current_user', methods=['GET'])
@jwt_required()
def current_user():
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id)
    
    account = User.query.get(user_id)
    role = "member"

    if not account:
        account = Doctor.query.get(user_id)
        role = "doctor"

    if not account:
        return jsonify({"message": "User account no longer exists"}), 404

    user_data = {
        "id": account.id,
        "username": account.username,
        "email": account.email,
        "role": getattr(account, "role", role),
        "is_verified": getattr(account, "is_verified", False),
    }

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
