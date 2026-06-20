from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
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
        role=data.get('role', 'learner'),  #since our main targets are learners, I set them as the default role.
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
        return jsonify({"error": "Your account has been suspended. Please contact support."}), 403 #403 is the http error is used to show"we know youbut you cant access your account atm
    
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
    current_user_id = get_jwt_identity()
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
        
        # we use the empty curly braces as a safety net incase the user sends nothing as an edit to prevent crashes
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