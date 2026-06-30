from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import JWTExtendedException
from flask_cors import CORS
from config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB cap on request body, needed for base64 flashcard images

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)

    @app.before_request
    def block_suspended_users():
        """Re-check is_active on every authenticated request so suspension takes effect immediately."""
        if request.method == 'OPTIONS':
            return None
        try:
            verify_jwt_in_request(optional=True)
        except JWTExtendedException:
            return None
        identity = get_jwt_identity()
        if identity is None:
            return None
        from app.models import User
        user = db.session.get(User, int(identity))
        if user and not user.is_active:
            return jsonify({"error": "Your account has been suspended. Please contact support."}), 403
        return None

    from app.routes.auth import auth_bp
    from app.routes.decks import decks_bp
    from app.routes.study import study_bp
    from app.routes.notifications import notifications_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(decks_bp, url_prefix='/api')
    app.register_blueprint(study_bp, url_prefix='/api')
    app.register_blueprint(notifications_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    
    
 # we keep the home route here as a guest can access it without authentication, 
    # and it serves as a health check endpoint for the API
    @app.route('/')
    def home():
        return {"status": "healthy", "message": "FlashLearn API is running successfully"}, 200

    return app