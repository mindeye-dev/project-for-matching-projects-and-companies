from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import json
from sqlalchemy.dialects.postgresql import ARRAY, JSON


db = SQLAlchemy()
migrate = Migrate()


class Opportunity(db.Model):
    __tablename__ = 'opportunity'

    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(256))
    client = db.Column(db.String(256))
    country = db.Column(db.String(128))
    sector = db.Column(db.String(128))
    summary = db.Column(db.Text)
    deadline = db.Column(db.String(64))
    program = db.Column(db.String(256))
    budget = db.Column(db.String(64))
    url = db.Column(db.String(512), unique=True)
    found = db.Column(db.Boolean, default=False, nullable=False)



class Partner(db.Model):
    __tablename__ = 'partner'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    country = db.Column(db.String(128))
    sector = db.Column(db.String(128))
    website = db.Column(db.String(512))
    linkedin_url = db.Column(db.String(512))
    linkedin_data = db.Column(JSON)

class Match(db.Model):
    __tablename__ = 'match'

    id = db.Column(db.Integer, primary_key=True)
    opportunity = db.Column(db.Integer)
    partner = db.Column(db.Integer)
    score = db.Column(db.Float)

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), default="user")  # 'user' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # relationship to sessions
    sessions = db.relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password = password

class Session(db.Model):
    __tablename__ = 'session'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    started_at = db.Column(db.DateTime, default = datetime.datetime.now(datetime.timezone.utc))
    ended_at = db.Column(db.DateTime, default = datetime.datetime.now(datetime.timezone.utc))

    # relationship to user
    user = db.relationship("User", back_populates="sessions")

    # relationship to messages
    messages = db.relationship("Message", back_populates="session", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "message_count": len(self.messages) if self.messages else 0,
            "messages": [m.to_dict() for m in self.messages]
        }

class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key = True)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id", name='fk_message_session_id'), nullable= False)
    role = db.Column(db.String(32), nullable = False)
    content = db.Column(db.Text, nullable = False)
    created_at = db.Column(db.DateTime, default = datetime.datetime.now(datetime.timezone.utc))

    __table_args__ = (
        db.UniqueConstraint('session_id', 'content', name='uq_session_content'),
    )

    # relationship to session
    session = db.relationship("Session", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role" : self.role,
            "content" : self.content,
            "created_at": self.created_at,
        }



