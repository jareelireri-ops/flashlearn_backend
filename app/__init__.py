from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS  # Import CORS
from config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

#  intialzing migrate for database migrations,jwt for authentication, and CORS to allow fluid communication with frontend 
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)  

    # registering the auth blueprint to the app and isolating auth routes under /api/auth 
    from app.routes.auth import auth_bp
    from app.routes.decks import decks_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(decks_bp, url_prefix='/api')

    # we keep the home route here as a guest can access it without authentication, 
    # and it serves as a health check endpoint for the API
    @app.route('/')
    def home():
        return {"status": "healthy", "message": "FlashLearn API is running successfully"}, 200

    return app