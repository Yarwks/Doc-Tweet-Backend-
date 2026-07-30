import re

from flask import jsonify, request
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User, Post, Doctor, Question
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app import app, 
from werkzeug.utils import secure_filename
import os


@app.route("/")
def index():
    return ""


@app.route("/db")
def db():
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
        return {"return": "Missing username or password"}

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return {"return": "Invalid username or password"}

    access_token = create_access_token(identity=str(user.id))

    return jsonify(
        {
            "message": "Log in success",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
            },
        }
    ), 200


@app.route("/api/auth/register/doctor", methods=["POST", "GET"])
def register_doctor():
    data = request.get_json() or {}
    errors = []

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirm_pass") or ""
    role = data.get("role") or ""
    is_verified = data.get("is_verified") or False

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


@app.route("/api/auth/register/member", methods=["POST", "GET"])
def register_member():
    data = request.get_json() or {}
    errors = []

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    confirm = data.get("confirm_pass") or ""
    role = data.get("role") or "member"

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


@app.route("/api/getposts", methods=["GET"])
def get_posts():
    posts = Post.query.all()
    posts_data = [
        {
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "author": post.author,
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
            "question": question.question,
            "answer": question.answer,
            "doctor": question.doctor,
        }
        for question in questions
    ]
    return jsonify(questions_data), 200


@app.route("/api/doctors", methods=["GET"])
def get_doctors():
    doctors = Doctor.query.all()
    doctors_data = [
        {"id": doctor.id, "name": doctor.name, "institution": doctor.institution}
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
        return jsonify({"success": True}), 200

@app.route('/api/current_user', methods=['GET'])
def current_user():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"message": "User account no longer exists"}), 444

    user_data = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_verified": user.is_verified if user.role == "doctor" else True
    }

    if user.role == 'doctor' and hasattr(user, 'doctor_profile'):
        user_data['doctor_profile'] = user.doctor_profile

    return jsonify(user_data), 200
