from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone
from sqlalchemy import func
from app import db
from app.models import User, Deck, Flashcard, Notification, ReviewHistory

# Initialize the Notifications Blueprint
notifications_bp = Blueprint('notifications', __name__)

# To keep notification creation consistent across the entire app I create a helper

def create_notification(user_id, message, notification_type=None, related_deck_id=None, related_flashcard_id=None):
    """Create and save a notification for a specific user."""
    notification = Notification(
        user_id=user_id,
        message=message,
        notification_type=notification_type,
        related_deck_id=related_deck_id,
        related_flashcard_id=related_flashcard_id
    )
    db.session.add(notification)
    return notification



# NOTIFICATION ROUTES-LIst,read,mark all as read, delete, check due cards



@notifications_bp.route('/notifications', methods=['GET'])
@jwt_required()
def list_notifications():
    """Get all notifications for the current user, newest first. Filter by ?unread=true for unread only."""
    current_user_id = int(get_jwt_identity())

    query = Notification.query.filter_by(user_id=current_user_id)

    unread_filter = request.args.get('unread')
    if unread_filter == 'true':
        query = query.filter_by(is_read=False)

    notifications = query.order_by(Notification.created_at.desc()).all()

    return jsonify([{
        "id": n.id,
        "message": n.message,
        "notification_type": n.notification_type,
        "is_read": n.is_read,
        "related_deck_id": n.related_deck_id,
        "related_flashcard_id": n.related_flashcard_id,
        "created_at": n.created_at.isoformat()
    } for n in notifications]), 200


@notifications_bp.route('/notifications/unread-count', methods=['GET'])
@jwt_required()
def unread_count():
    """Get the count of unread notifications — used for badge display on the frontend."""
    current_user_id = int(get_jwt_identity())

    count = Notification.query.filter_by(
        user_id=current_user_id,
        is_read=False
    ).count()

    return jsonify({"unread_count": count}), 200


@notifications_bp.route('/notifications/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_as_read(notification_id):
    """Mark a single notification as read."""
    current_user_id = int(get_jwt_identity())
    notification = db.session.get(Notification, notification_id)

    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    if notification.user_id != current_user_id:
        return jsonify({"error": "Unauthorized to access this notification"}), 403

    notification.is_read = True

    try:
        db.session.commit()
        return jsonify({"message": "Notification marked as read"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"mark_as_read failed for notification_id={notification_id}: {str(e)}")
        return jsonify({"error": "Failed to update notification", "details": str(e)}), 500


@notifications_bp.route('/notifications/read-all', methods=['PUT'])
@jwt_required()
def mark_all_as_read():
    """Mark all of the current user's notifications as read in one go."""
    current_user_id = int(get_jwt_identity())

    try:
        Notification.query.filter_by(
            user_id=current_user_id,
            is_read=False
        ).update({"is_read": True})
        db.session.commit()
        return jsonify({"message": "All notifications marked as read"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"mark_all_as_read failed for user_id={current_user_id}: {str(e)}")
        return jsonify({"error": "Failed to update notifications", "details": str(e)}), 500


@notifications_bp.route('/notifications/<int:notification_id>', methods=['DELETE'])
@jwt_required()
def delete_notification(notification_id):
    """Delete a single notification."""
    current_user_id = int(get_jwt_identity())
    notification = db.session.get(Notification, notification_id)

    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    if notification.user_id != current_user_id:
        return jsonify({"error": "Unauthorized to delete this notification"}), 403

    try:
        db.session.delete(notification)
        db.session.commit()
        return jsonify({"message": "Notification deleted"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"delete_notification failed for notification_id={notification_id}: {str(e)}")
        return jsonify({"error": "Failed to delete notification", "details": str(e)}), 500



# This route checks if the user has any cards due for review and creates a notification if one doesn't already exist for today.
# It can be called from the frontend when the user logs in or opens the app,
# or it can be scheduled as a background task to run daily.



@notifications_bp.route('/notifications/check-due', methods=['POST'])
@jwt_required()
def check_due_cards():
    """Check if the user has cards due for review and create a notification if so."""
    current_user_id = int(get_jwt_identity())
    now = datetime.now(timezone.utc)

    # Same logic as the review queue
    latest_review_sub = db.session.query(
        ReviewHistory.flashcard_id,
        func.max(ReviewHistory.reviewed_at).label('latest')
    ).filter(
        ReviewHistory.user_id == current_user_id
    ).group_by(ReviewHistory.flashcard_id).subquery()

    cards_due = db.session.query(func.count()).select_from(ReviewHistory).join(
        latest_review_sub,
        db.and_(
            ReviewHistory.flashcard_id == latest_review_sub.c.flashcard_id,
            ReviewHistory.reviewed_at == latest_review_sub.c.latest
        )
    ).filter(
        ReviewHistory.user_id == current_user_id,
        ReviewHistory.next_review_date <= now
    ).scalar()

    if not cards_due or cards_due == 0:
        return jsonify({"message": "No cards due", "cards_due": 0}), 200

    # Only create a notification if we haven't already sent one today for the cards that ae due
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    existing_today = Notification.query.filter(
        Notification.user_id == current_user_id,
        Notification.notification_type == 'review_due',
        Notification.created_at >= today_start
    ).first()

    if existing_today:
        return jsonify({"message": "Already notified today", "cards_due": cards_due}), 200

    create_notification(
        user_id=current_user_id,
        message=f"You have {cards_due} card(s) due for review today!",
        notification_type='review_due'
    )

    try:
        db.session.commit()
        return jsonify({"message": "Due card notification created", "cards_due": cards_due}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"check_due_cards failed for user_id={current_user_id}: {str(e)}")
        return jsonify({"error": "Failed to create notification", "details": str(e)}), 500