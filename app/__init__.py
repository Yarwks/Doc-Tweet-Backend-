from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from flask_migrate import Migrate
from app import routes

app = Flask(__name__)
db = SQLAlchemy(app)
migrate = Migrate(app, db)


