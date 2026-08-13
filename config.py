import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    
    # Use DATABASE_URL from environment (for Render PostgreSQL) or fallback to SQLite
    # Use postgresql+psycopg for psycopg3 compatibility
    db_url = os.environ.get('DATABASE_URL') or 'sqlite:///retrix.db'
    if db_url:
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif db_url.startswith('postgresql://') and '+psycopg' not in db_url and '+psycopg2' not in db_url:
            db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
