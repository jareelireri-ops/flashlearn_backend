import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt_identity
from flask_jwt_extended.exceptions import JWTExtendedException
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from config import Config

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()


def configure_logging(app):
    """Sets up one shared logger for the whole app: a rotating file (so logs
    don't grow forever) plus console output, so errors are recorded even
    when nobody is watching the terminal."""
    if app.logger.handlers:
        return  # avoid duplicate handlers when Flask's reloader restarts in debug mode

    log_dir = os.path.join(app.root_path, '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)s: %(message)s'
    )

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'flashlearn.log'), maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB cap on request body, needed for base64 images

    configure_logging(app)

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

    @app.after_request
    def log_request(response):
        """One line per request: who hit what, and what came back."""
        app.logger.info(
            '%s %s -> %s', request.method, request.path, response.status_code
        )
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Covers abort(404), abort(403), etc. so they return the same JSON
        shape as everything else instead of Flask's default HTML error page."""
        app.logger.warning('%s %s -> %s: %s', request.method, request.path, e.code, e.description)
        return jsonify({"error": e.description}), e.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e):
        """Catches anything not already wrapped in its route's own try/except.
        Logs the full traceback
        so it's actually debuggable, but never leaks that detail to the client."""
        app.logger.exception('Unhandled exception on %s %s', request.method, request.path)
        return jsonify({"error": "Something went wrong on our end. Please try again."}), 500

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