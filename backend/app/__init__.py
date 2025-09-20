# https://docs.langchain.com/langsmith/observability-quickstart#application-code
from flask import Flask
from flask_cors import CORS

from .routes.api import api_bp
from .routes.auth import auth_bp
from flask_jwt_extended import JWTManager
from .models import db
from .scrapers_of_projects.scheduled_scraper import run_scraping, stop_scraping


def create_app():
     app = Flask(__name__)
     app.config.from_object("app.config.Config")
     print(app.config['SQLALCHEMY_DATABASE_URI'])
     db.init_app(app)
     try:
          with app.app_context():
               db.create_all()  # Create tables
          print("Tables created successfully.")
     except Exception as e:
          print(f"Error creating tables: {e}")
    
     # Configure CORS to allow the frontend URL
     CORS(app, 
          origins=[app.config['FRONTEND_URL']], 
          supports_credentials=True,
          allow_headers=["Content-Type", "Authorization"],
          methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
     JWTManager(app)

     app.register_blueprint(api_bp, url_prefix="/api")
     app.register_blueprint(auth_bp, url_prefix="/api/auth")
    
     #run_scraping()
    
     return app
