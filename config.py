import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///retrix.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
