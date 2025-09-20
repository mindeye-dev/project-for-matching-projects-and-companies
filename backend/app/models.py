from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from flask_sqlalchemy import SQLAlchemy
import json
from sqlalchemy.dialects.postgresql import ARRAY, JSON


db = SQLAlchemy()


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
    found = db.Column(db.Boolean, default=False, nullable=False)
    # Use Text to store the JSON data as a string
    three_matched_scores_and_recommended_partners_ids = db.Column(db.Text)

    def set_three_matched_scores_and_recommended_partners_ids(self, value):
        # Convert Python list or dict to a JSON string
        self.three_matched_scores_and_recommended_partners_ids = json.dumps(value)

    def get_three_matched_scores_and_recommended_partners_ids(self):
        # Convert JSON string back to a Python object (list or dict)
        return json.loads(self.three_matched_scores_and_recommended_partners_ids) if self.three_matched_scores_and_recommended_partners_ids else []



class Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    country = db.Column(db.String(128))
    sector = db.Column(db.String(128))
    website = db.Column(db.String(512))
    linkedindata = db.Column(JSON)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), default="user")  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password = password

