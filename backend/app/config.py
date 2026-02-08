# there is not SQLALCHEMY_DATABASE_URI  is not used in this project.


import os
import warnings


def _get_jwt_secret():
    """Get JWT secret key with warning if not set"""
    jwt_secret = os.environ.get("JWT_SECRET_KEY")
    if not jwt_secret:
        warnings.warn(
            "JWT_SECRET_KEY not set! Using a default key is insecure. "
            "Please set JWT_SECRET_KEY in your .env file.",
            UserWarning
        )
        return "CHANGE_THIS_IN_PRODUCTION"  # Temporary fallback for development only
    return jwt_secret


class Config:
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8080")
    
    # JWT Secret Key - MUST be set via environment variable for security
    # ⚠️ WARNING: Default value is insecure. Always set JWT_SECRET_KEY in production!
    JWT_SECRET_KEY = _get_jwt_secret()
    
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    
    # Microsoft Teams Configuration
    TEAMS_APP_ID = os.environ.get("TEAMS_APP_ID", "")
    TEAMS_APP_PASSWORD = os.environ.get("TEAMS_APP_PASSWORD", "")

