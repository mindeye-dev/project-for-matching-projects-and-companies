from . import db
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(256))
    client = db.Column(db.String(256))
    country = db.Column(db.String(128))
    sector = db.Column(db.String(128))
    summary = db.Column(db.Text)
    deadline = db.Column(db.String(64))
    program = db.Column(db.String(256))
    budget = db.Column(db.String(64))
    url = db.Column(db.String(512))
    score = db.Column(db.Integer)

class Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    country = db.Column(db.String(128))
    sector = db.Column(db.String(128))
    website = db.Column(db.String(512))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), default='user')  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password) 