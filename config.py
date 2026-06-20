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