from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta
import secrets
from app import db
from app.models import User

# Initialize the Authentication Blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    
    # Check for required validation fields
    if 'email' not in data or 'password' not in data or 'name' not in data:
        return jsonify({"error": "Missing required fields (name, email, password)"}), 400
    
    #we strip the spaces and convert the email to lowercase as we did in models.py.
    email_input = data['email'].strip().lower()
        
    # Enforce unique email check , using .first() to stop the query after finding the first match.
    if User.query.filter_by(email=email_input).first():
        return jsonify({"error": "This email address is already registered"}), 400

    # Securely hash the user password
    hashed_password = generate_password_hash(data['password'])
    
    # Create database user record instance mapping to the ERD columns
    new_user = User(
        name=data['name'],
        email=email_input,
        password_hash=hashed_password,
        role='learner',  # always learner on register; admin is seeded separately
        is_active=True
    )
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"message": "User has been registered successfully", "user_id": new_user.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Database recording failed", "details": str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    
    if 'email' not in data or 'password' not in data:
        return jsonify({"error": "Missing email or password"}), 400
        
    # since in models.py we save it in lowercase,to avoid errors/duplication due to casesensitivity when logging in,
    email_input = data['email'].strip().lower()
    
    # Fetch the user record based on the provided email
    user = User.query.filter_by(email=email_input).first()
    
    # Verify that the user exists and that the provided password matches the hashed password
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({"error": "Invalid email or password"}), 401
        
    # before generating a jwt,we check if the admin has suspended the account.
    if not user.is_active:
        return jsonify({"error": "Your account has been suspended. Please contact support."}), 403
    
    # Generate a JWT access token with the user's ID as the identity claim, this will be used for authenticated requests to protected endpoints
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }), 200


@auth_bp.route('/profile', methods=['GET', 'PUT'])
@jwt_required()
def profile():
    # get the current user's ID from the JWT token and fetch their profile from the database.
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    
    if not user:
        return jsonify({"error": "The user profile has not been found"}), 404
        
    if request.method == 'GET':
        return jsonify({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "profile_picture_url": user.profile_picture_url,
            "is_active": user.is_active,
            "created_at": user.created_at
        }), 200
        
    # we use the empty curly braces as a safety net incase the user sends nothing as an edit,,to prevent crashes
    elif request.method == 'PUT':
        data = request.get_json() or {}
        
        # allow users to update their name and profile picture, but not their email or role through this endpoint .
        if 'name' in data:
            user.name = data['name']
        if 'profile_picture_url' in data:
            user.profile_picture_url = data['profile_picture_url']
            
        try:
            db.session.commit()
            return jsonify({"message": "Profile has been updated successfully"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Failed to update the database profile rows", "details": str(e)}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}

    if 'email' not in data:
        return jsonify({"error": "Email is required"}), 400

    email_input = data['email'].strip().lower()
    user = User.query.filter_by(email=email_input).first()

    if not user:
        return jsonify({"message": "If that email exists, a reset link has been sent"}), 200

    token = secrets.token_urlsafe(32)
    user.password_reset_token = token
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)

    try:
        db.session.commit()
        response = {"message": "If that email exists, a reset link has been sent"}
        # dev-only: keeps local testing working until you wire up email in production
        if current_app.config.get('DEV_RETURN_RESET_TOKEN'):
            response["reset_token"] = token
        return jsonify(response), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to generate reset token", "details": str(e)}), 500


# a passwordreset feature that allows users to reset their password using a token sent to their email, 
# and it also checks for token expiration to enhance security.
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json() or {}

    if 'token' not in data or 'new_password' not in data:
        return jsonify({"error": "Token and new_password are required"}), 400

    user = User.query.filter_by(password_reset_token=data['token']).first()

    if not user:
        return jsonify({"error": "Invalid or expired reset token"}), 400

# adding a check to see if the reset token has expired, and if so,
# we clear the token and expiration fields in the database to prevent reuse of an expired token.
    if user.password_reset_expires < datetime.now(timezone.utc):
        user.password_reset_token = None
        user.password_reset_expires = None
        db.session.commit()
        return jsonify({"error": "Reset token has expired, please request a new one"}), 400

    user.password_hash = generate_password_hash(data['new_password'])
    user.password_reset_token = None
    user.password_reset_expires = None

    try:
        db.session.commit()
        return jsonify({"message": "Password has been reset successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to reset password", "details": str(e)}), 500