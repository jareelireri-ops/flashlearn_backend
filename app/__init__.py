from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from config import Config

# initializing of the database, migration tool, and JWT manager for the Flask application
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

# creating a function that is the master switch for the flask app(allows configuration set up and connects the db,migration and JWT)
def create_app(config_class=Config):
    app = Flask(__name__)
    # load the class we created in config.py inorder to use the settings defined there
    app.config.from_object(config_class)

    # Connecting the database, migrations, and login security to the running app
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    # Importing the routes and models to register them with the app

    return app