from app import app, login_manager, db
from sqlalchemy import text
from flask import request, jsonify
import re
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import User 
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

    