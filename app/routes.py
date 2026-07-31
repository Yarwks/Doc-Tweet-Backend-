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
    return ""


@app.route('/db')
def db_check():
    try:
        db.session.execute(text("SELECT 1"))
        return {"db": "ok"}, 200
    except Exception as e:
        return {"db": "error", "details": str(e)}, 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid username or password"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role}
    )

    return jsonify({
        "message": "Log in success",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        }
    }), 200


@app.route("/api/auth/register/doctor", methods=["POST", "GET"])
def register_doctor():
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
            role="doctor",
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
            "title": post.title,
            "content": post.content,
            "author": post.author,
            "image_url": post.image_url,
            "likes_count": post.likes_count,
            "created_at": post.created_at.isoformat() if post.created_at else None,
        }
        for post in posts
    ]
    return jsonify(posts_data), 200


@app.route("/api/getquestions", methods=["GET"])
def get_questions():
    questions = Question.query.all()
    questions_data = [
        {
            "id": question.id,
            "title": question.title,
            "content": question.content,
            "author": question.author,
            "is_anonymous": question.is_anonymous,
            "is_resolved": question.is_resolved,
            "created_at": question.created_at.isoformat() if question.created_at else None,
        }
        for question in questions
    ]
    return jsonify(questions_data), 200


@app.route("/api/doctors", methods=["GET"])
def get_doctors():
    doctors = Doctor.query.all()
    doctors_data = [
        {
            "id": doctor.id,
            "username": doctor.username,
            "email": doctor.email,
            "institution": doctor.institution,
            "specialization": doctor.specialization,
            "avatar_url": doctor.avatar_url,
            "is_verified": doctor.is_verified,
            "created_at": doctor.created_at.isoformat() if doctor.created_at else None,
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
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"message": "User account no longer exists"}), 444

    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_verified": user.is_verified,
    }

    return jsonify(user_data), 200
