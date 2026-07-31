import re
import os

from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
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
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
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

    return jsonify(user_data), 200