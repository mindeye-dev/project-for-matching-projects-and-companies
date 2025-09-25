# there is not SQLALCHEMY_DATABASE_URI  is not used in this project.


import os


class Config:
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:8080")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "u23y4y23&98237(****K)")
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
 