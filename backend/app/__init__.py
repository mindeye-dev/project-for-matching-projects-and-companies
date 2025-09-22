# https://docs.langchain.com/langsmith/observability-quickstart#application-code
from flask import Flask
from flask_cors import CORS
import threading
import time

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
    
    # Configure CORS - permissive for development
    CORS(app, 
         origins="*",  # Allow all origins for development
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    
    JWTManager(app)

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    
    # Start scraping after a short delay to ensure app is ready
    def delayed_scraping():
        time.sleep(2)  # Wait 2 seconds for app to be ready
        try:
            run_scraping()
        except Exception as e:
            print(f"Error in background scraping: {e}")
    
    # Start scraping in a separate thread
    scraping_thread = threading.Thread(target=delayed_scraping, daemon=True)
    scraping_thread.start()
    
    return app
