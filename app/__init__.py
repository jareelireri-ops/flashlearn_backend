from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import Config

# 1. Create the database and security tools (unattached for now)
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

# 2. Build the application factory
def create_app(config_class=Config):
    app = Flask(__name__)
    
    # Load the settings from your config.py file
    app.config.from_object(config_class)

    # Attach the database and security tools to this specific app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # (We will connect your routes/models here in the next step)

    return app