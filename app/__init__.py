import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_cors import CORS

app = Flask(__name__)


app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY' , 'dev-only-key')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] =False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
jwt = JWTManager(app)
login_manager.login_view = 'login'

from flask_cors import CORS

#We need to add the deployed vercel app url 
CORS(app, origins=[
    "http://localhost:5173",           
    "https://your-app.vercel.app",    
])

from app import routes