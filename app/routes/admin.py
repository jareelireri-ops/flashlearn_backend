from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models import User, Deck, Flashcard, Report

# Initializing Admin Blueprint
admin_bp = Blueprint('admin', __name__)

# check the role in the db
def is_admin(user_id):
    user = db.session.get(User, user_id)
    return user and user.role == 'admin'

#
# 
#CONTENT REPORTING (For users)

@admin_bp.route('/reports', methods=['POST'])
@jwt_required()
def submit_report():
    """Submit a report for an inappropriate deck or flashcard."""
    current_user_id = int(get_jwt_identity())

    # Admins review reports, they don't file them - this also closes off the
    # API path that the frontend role-gating alone wouldn't stop (e.g. curl/Postman).
    if is_admin(current_user_id):
        return jsonify({"error": "Admins review reports, not submit them"}), 403

    data = request.get_json() or {}
    
    reason = data.get('reason')
    if not reason:
        return jsonify({"error": "Reason for reporting is required"}), 400
        
    deck_id = data.get('deck_id')
    flashcard_id = data.get('flashcard_id')
    
    if not deck_id and not flashcard_id:
        return jsonify({"error": "Must provide either deck_id or flashcard_id"}), 400
        
    new_report = Report(
        reporter_id=current_user_id,
        deck_id=deck_id,
        flashcard_id=flashcard_id,
        reason=reason
    )
    
    try:
        db.session.add(new_report)
        db.session.commit()
        return jsonify({"message": "Report submitted successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to submit report", "details": str(e)}), 500



#For Admins only


@admin_bp.route('/admin/users', methods=['GET'])
@jwt_required()
def get_all_users():
    """View all users."""
    current_user_id = int(get_jwt_identity())
    if not is_admin(current_user_id):
        return jsonify({"error": "Admin access required"}), 403
        
    users = User.query.all()
    return jsonify([{
        "id": u.id,
        "email": u.email,
        "name": u.name,
        "role": u.role,
        "is_active": u.is_active,
        "created_at": u.created_at
    } for u in users]), 200

@admin_bp.route('/admin/users/<int:user_id>/status', methods=['PUT'])
@jwt_required()
def update_user_status(user_id):
    """Suspend or reactivate a user."""
    current_user_id = int(get_jwt_identity())
    if not is_admin(current_user_id):
        return jsonify({"error": "Admin access required"}), 403
        
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    if user.role == 'admin':
        return jsonify({"error": "Cannot suspend another admin"}), 400
        
    data = request.get_json() or {}
    
    if 'is_active' in data:
        user.is_active = data['is_active']
        
    try:
        db.session.commit()
        status_msg = "reactivated" if user.is_active else "suspended"
        return jsonify({"message": f"User successfully {status_msg}"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update user status", "details": str(e)}), 500

@admin_bp.route('/admin/reports', methods=['GET'])
@jwt_required()
def get_reports():
    """View all content reports."""
    current_user_id = int(get_jwt_identity())
    if not is_admin(current_user_id):
        return jsonify({"error": "Admin access required"}), 403
        
    status = request.args.get('status') #filter by pending, reviewed, resolved
    
    query = Report.query
    if status:
        query = query.filter_by(status=status)
        
    reports = query.all()
    return jsonify([{
        "id": r.id,
        "reporter_id": r.reporter_id,
        "deck_id": r.deck_id,
        "flashcard_id": r.flashcard_id,
        "reason": r.reason,
        "status": r.status,
        "created_at": r.created_at
    } for r in reports]), 200

@admin_bp.route('/admin/reports/<int:report_id>', methods=['PUT'])
@jwt_required()
def resolve_report(report_id):
    """Update a report's status (mark as resolved)."""
    current_user_id = int(get_jwt_identity())
    if not is_admin(current_user_id):
        return jsonify({"error": "Admin access required"}), 403
        
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({"error": "Report not found"}), 404
        
    data = request.get_json() or {}
    if 'status' in data:
        report.status = data['status']
        
    try:
        db.session.commit()
        return jsonify({"message": "Report status updated"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update report", "details": str(e)}), 500

@admin_bp.route('/admin/content', methods=['DELETE'])
@jwt_required()
def admin_delete_content():
    """Remove inappropriate decks or flashcards as an admin."""
    current_user_id = int(get_jwt_identity())
    if not is_admin(current_user_id):
        return jsonify({"error": "Admin access required"}), 403
        
    deck_id = request.args.get('deck_id')
    flashcard_id = request.args.get('flashcard_id')
    
    try:
        if deck_id:
            deck = db.session.get(Deck, int(deck_id))
            if deck:
                db.session.delete(deck)
                db.session.commit()
                return jsonify({"message": "Deck forcibly removed"}), 200
                
        elif flashcard_id:
            card = db.session.get(Flashcard, int(flashcard_id))
            if card:
                db.session.delete(card)
                db.session.commit()
                return jsonify({"message": "Flashcard forcibly removed"}), 200
                
        return jsonify({"error": "Content not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to remove content", "details": str(e)}), 500