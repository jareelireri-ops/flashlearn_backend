import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from the .env file 
load_dotenv()

class Config:
    # this class holds all the configuration settings for the Flask application
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # configuration of the database for postgres, using environment variables for flexibility and security
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/flashlearn_db')
    
    # since the app does not need a signaling feature, disable sqlalchemy-track modifications
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # jwt for authentication and secret key for signing iN, using environment variables for security
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret-key-change-in-production')
    
    # setting the expiration time for the token at 2 hours,to be adjusted based on the security requirements of the application
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=2)

    # The production CORS whitelist: URLs permitted to make requests to our API 
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get(
            'CORS_ORIGINS',
            'http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173'
        ).split(',')
        if origin.strip()
    ]

    # local dev only: return reset_token in forgot-password JSON when no email service is wired up yet
    DEV_RETURN_RESET_TOKEN = os.environ.get('DEV_RETURN_RESET_TOKEN', 'false').lower() == 'true'