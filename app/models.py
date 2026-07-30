
from flask_login import UserMixin
from app import db
from datetime import datetime
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"

    def to_dict(self, with_favorites=False):
      data = {
        "id": self.id,
        "username": self.username,
        "email": self.email,
        "avatar_url": self.avatar_url,
        "created_at": self.created_at.isoformat() if self.created_at else None,
    }
      if with_favorites:
        favorites = Favorite.query.filter_by(user_id=self.id).all()
        data["favorite_doctors"] = [f.doctor.to_dict() for f in favorites]
      return data

class Doctor(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    institution = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    avatar_url = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    specialization = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Doctor {self.username}"
    
    def to_dict(self):
        return {
        "id": self.id,
        "username": self.username,
        "email": self.email,
        "institution": self.institution,
        "specialization": self.specialization,
        "avatar_url": self.avatar_url,
        "is_verified": self.is_verified,
        "created_at": self.created_at.isoformat() if self.created_at else None,
    }

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)
    likes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Post {self.title}"

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    is_resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=func.now())
    answers = db.relationship('Answer', backref='question', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f"<Question {self.title}"
    

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    author = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=True)
    is_doctor_answer = db.Column(db.Boolean, default=False)
    likes_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=func.now())

    def __repr__(self) -> str:
        return f"<Answer {self.id}"

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=func.now())
    doctor = db.relationship('Doctor', backref='favorited_by', lazy=True)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'doctor_id', name='unique_user_doctor_favorite'),
    )

    def __repr__(self):
        return f"<Favorite user={self.user_id} doctor={self.doctor_id}>"    