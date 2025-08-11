from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from .routes.api import api_bp
from .routes.auth import auth_bp
from flask_jwt_extended import JWTManager

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this in production!
    db.init_app(app)
    CORS(app)
    JWTManager(app)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    return app 