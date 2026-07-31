import os
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DB_PATH = os.path.join(BASE_DIR, 'doctweet.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

app = Flask(__name__)

app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-only-key')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_DIR

# Allow all origins & methods during development so OPTIONS preflight passes seamlessly
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=True,
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"]
)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
jwt = JWTManager(app)

# Import routes at the very end so they attach to the initialized app object
from app import routes
from app.models import User, Doctor, Post, Question, Answer


def seed_demo_data():
    admin = User.query.filter_by(username='admin_demo').first()
    doctor = Doctor.query.filter_by(username='dr_demo').first()
    member = User.query.filter_by(username='member_demo').first()

    if not admin:
        admin = User(
            username='admin_demo',
            email='admin@example.com',
            password_hash=generate_password_hash('adminpass'),
            role='admin',
            is_verified=True,
        )
        db.session.add(admin)

    if not doctor:
        doctor = Doctor(
            username='dr_demo',
            email='doctor@example.com',
            institution='City Health Center',
            password_hash=generate_password_hash('doctorpass'),
            specialization='General Medicine',
            role='doctor',
            is_verified=True,
        )
        db.session.add(doctor)

    if not member:
        member = User(
            username='member_demo',
            email='member@example.com',
            password_hash=generate_password_hash('memberpass'),
            role='member',
            is_verified=False,
        )
        db.session.add(member)

    db.session.flush()

    if not Post.query.first():
        post = Post(
            title='Welcome to DocTweet',
            content='This is a sample post created for local development testing.',
            author='dr_demo',
            doctor_id=doctor.id,
            image_url=None,
            likes_count=7,
        )
        db.session.add(post)

    if not Question.query.first():
        question = Question(
            title='How do I stay hydrated?',
            content='I am looking for general tips on daily hydration and nutrition.',
            author='member_demo',
            user_id=member.id,
            is_anonymous=False,
            is_resolved=False,
        )
        db.session.add(question)
        db.session.flush()

        answer = Answer(
            content='Aim for consistent water intake throughout the day and adjust based on activity level.',
            question_id=question.id,
            author='dr_demo',
            doctor_id=doctor.id,
            is_doctor_answer=True,
            likes_count=3,
        )
        db.session.add(answer)

    db.session.commit()


with app.app_context():
    db.create_all()
    seed_demo_data()