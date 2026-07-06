from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, desc
from app import db
from app.models import User, Deck, Flashcard, StudySession, ReviewHistory

# Initialize the Study Blueprint
study_bp = Blueprint('study', __name__)

# SPACED REPETITION INTERVALS to determine when a card should be reviewed again
# based on how the user rated it.

REVIEW_INTERVALS = {
    'easy': timedelta(days=7),
    'medium': timedelta(days=3),
    'hard': timedelta(days=1),
}

# A user can study a deck if they created it, saved it to their collection, or it's public.

def user_can_access_deck(user, deck):
    """Check if a user has permission to study a specific deck."""
    if deck.creator_id == user.id:
        return True
    if deck.is_public:
        return True
    if deck in user.saved_decks:
        return True
    return False

# STUDY SESSION CONTROL TO START, PAUSE, RESUME, COMPLETE, AND REVIEW CARDS

@study_bp.route('/study/<int:deck_id>/start', methods=['POST'])
@jwt_required()
def start_session(deck_id):
    """Start a new study session for a deck, or resume an existing unfinished one."""
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    deck = db.session.get(Deck, deck_id)

    if not deck:
        return jsonify({"error": "Deck not found"}), 404

    if not user_can_access_deck(user, deck):
        return jsonify({"error": "You do not have access to this deck"}), 403

    card_count = Flashcard.query.filter_by(deck_id=deck_id).count()
    if card_count == 0:
        return jsonify({"error": "This deck has no flashcards to study"}), 400

    existing_session = StudySession.query.filter_by(
        user_id=current_user_id,
        deck_id=deck_id
    ).filter(
        StudySession.status.in_(['in-progress', 'paused'])
    ).first()

    if existing_session:
        data = request.get_json() or {}
        if data.get('force_new'):
            existing_session.status = 'completed'
            existing_session.end_time = datetime.now(timezone.utc)
            db.session.commit()
        else:
            if existing_session.status == 'paused':
                existing_session.status = 'in-progress'
                db.session.commit()
            
            # Fetch ratings already submitted before the pause
            previous_reviews = ReviewHistory.query.filter_by(session_id=existing_session.id).all()
            session_ratings = {r.flashcard_id: r.rating for r in previous_reviews}
                
            return jsonify({
                "message": "Resuming existing session",
                "session": {
                    "id": existing_session.id,
                    "deck_id": existing_session.deck_id,
                    "status": existing_session.status,
                    "current_card_index": existing_session.current_card_index,
                    "total_cards": card_count,
                    "start_time": existing_session.start_time.isoformat()
                },
                "session_ratings": session_ratings
            }), 200

    new_session = StudySession(
        user_id=current_user_id,
        deck_id=deck_id,
        status='in-progress',
        current_card_index=0
    )

    try:
        db.session.add(new_session)
        db.session.commit()
        return jsonify({
            "message": "Study session started",
            "session": {
                "id": new_session.id,
                "deck_id": new_session.deck_id,
                "status": new_session.status,
                "current_card_index": 0,
                "total_cards": card_count,
                "start_time": new_session.start_time.isoformat()
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"start_session failed for deck_id={deck_id}: {str(e)}")
        return jsonify({"error": "Failed to start session", "details": str(e)}), 500

@study_bp.route('/study/<int:deck_id>/active', methods=['GET'])
@jwt_required()
def get_active_session(deck_id):
    """Check if a user has an active or paused session for a deck."""
    current_user_id = int(get_jwt_identity())
    
    session = StudySession.query.filter_by(
        user_id=current_user_id,
        deck_id=deck_id
    ).filter(
        StudySession.status.in_(['in-progress', 'paused'])
    ).first()

    if not session:
        return jsonify({"error": "No active session found"}), 404

    return jsonify({
        "session": {
            "id": session.id,
            "deck_id": session.deck_id,
            "status": session.status,
            "current_card_index": session.current_card_index,
            "start_time": session.start_time.isoformat()
        }
    }), 200

@study_bp.route('/study/sessions/<int:session_id>/card', methods=['GET'])
@jwt_required()
def get_current_card(session_id):
    """Get the current flashcard for an active study session."""
    current_user_id = int(get_jwt_identity())
    session = db.session.get(StudySession, session_id)

    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session.user_id != current_user_id:
        return jsonify({"error": "Unauthorized to access this session"}), 403

    if session.status == 'completed':
        return jsonify({"error": "This session is already completed"}), 400

    direction = request.args.get('direction', 'current')

    if direction == 'next':
        session.current_card_index += 1
    elif direction == 'prev':
        if session.current_card_index > 0:
            session.current_card_index -= 1

    cards = Flashcard.query.filter_by(
        deck_id=session.deck_id
    ).order_by(Flashcard.created_at).all()

    total_cards = len(cards)

    if session.current_card_index >= total_cards:
        db.session.commit()
        return jsonify({
            "session_complete": True,
            "message": "You have reviewed all cards in this deck!",
            "total_cards": total_cards,
            "current_card_index": session.current_card_index
        }), 200

    current_card = cards[session.current_card_index]

    try:
        db.session.commit()
        return jsonify({
            "session_complete": False,
            "current_card_index": session.current_card_index,
            "total_cards": total_cards,
            "flashcard": {
                "id": current_card.id,
                "question": current_card.question,
                "answer": current_card.answer,
                "difficulty_level": current_card.difficulty_level,
                "image_url": current_card.image_url
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"get_current_card failed for session_id={session_id}: {str(e)}")
        return jsonify({"error": "Failed to fetch card", "details": str(e)}), 500

@study_bp.route('/study/sessions/<int:session_id>/review', methods=['POST'])
@jwt_required()
def review_card(session_id):
    """Submit a review rating (easy/medium/hard) for the current flashcard."""
    current_user_id = int(get_jwt_identity())
    session = db.session.get(StudySession, session_id)

    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session.user_id != current_user_id:
        return jsonify({"error": "Unauthorized to access this session"}), 403

    if session.status != 'in-progress':
        if session.status == 'paused':
            session.status = 'in-progress'
        else:
            return jsonify({"error": "Session is not in progress"}), 400

    data = request.get_json() or {}

    if 'flashcard_id' not in data:
        return jsonify({"error": "flashcard_id is required"}), 400

    if 'rating' not in data or data['rating'] not in REVIEW_INTERVALS:
        return jsonify({"error": "Rating must be one of: easy, medium, hard"}), 400

    flashcard = db.session.get(Flashcard, data['flashcard_id'])
    if not flashcard:
        return jsonify({"error": "Flashcard not found"}), 404

    if flashcard.deck_id != session.deck_id:
        return jsonify({"error": "This flashcard does not belong to the current study deck"}), 400

    rating = data['rating']
    now = datetime.now(timezone.utc)
    next_review = now + REVIEW_INTERVALS[rating]

    review = ReviewHistory(
        user_id=current_user_id,
        flashcard_id=flashcard.id,
        session_id=session.id,
        rating=rating,
        reviewed_at=now,
        next_review_date=next_review
    )

    session.current_card_index += 1

    try:
        db.session.add(review)
        db.session.commit()
        return jsonify({
            "message": "Review recorded",
            "review": {
                "flashcard_id": flashcard.id,
                "rating": rating,
                "next_review_date": next_review.isoformat()
            },
            "current_card_index": session.current_card_index
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"review_card failed for session_id={session_id}: {str(e)}")
        return jsonify({"error": "Failed to record review", "details": str(e)}), 500

@study_bp.route('/study/sessions/<int:session_id>/pause', methods=['PUT'])
@jwt_required()
def pause_session(session_id):
    """Pause an active study session."""
    current_user_id = int(get_jwt_identity())
    session = db.session.get(StudySession, session_id)

    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session.user_id != current_user_id:
        return jsonify({"error": "Unauthorized to access this session"}), 403

    if session.status != 'in-progress':
        return jsonify({"error": "Only in-progress sessions can be paused"}), 400

    session.status = 'paused'

    try:
        db.session.commit()
        return jsonify({"message": "Session paused", "current_card_index": session.current_card_index}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"pause_session failed for session_id={session_id}: {str(e)}")
        return jsonify({"error": "Failed to pause session", "details": str(e)}), 500

@study_bp.route('/study/sessions/<int:session_id>/resume', methods=['PUT'])
@jwt_required()
def resume_session(session_id):
    """Resume a paused study session."""
    current_user_id = int(get_jwt_identity())
    session = db.session.get(StudySession, session_id)

    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session.user_id != current_user_id:
        return jsonify({"error": "Unauthorized to access this session"}), 403

    if session.status != 'paused':
        return jsonify({"error": "Only paused sessions can be resumed"}), 400

    session.status = 'in-progress'

    try:
        db.session.commit()
        # Fetch ratings already submitted before the pause
        previous_reviews = ReviewHistory.query.filter_by(session_id=session.id).all()
        session_ratings = {r.flashcard_id: r.rating for r in previous_reviews}
        
        return jsonify({
            "message": "Session resumed", 
            "current_card_index": session.current_card_index,
            "session_ratings": session_ratings
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"resume_session failed for session_id={session_id}: {str(e)}")
        return jsonify({"error": "Failed to resume session", "details": str(e)}), 500

@study_bp.route('/study/sessions/<int:session_id>/complete', methods=['PUT'])
@jwt_required()
def complete_session(session_id):
    """Mark a study session as completed."""
    current_user_id = int(get_jwt_identity())
    session = db.session.get(StudySession, session_id)

    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session.user_id != current_user_id:
        return jsonify({"error": "Unauthorized to access this session"}), 403

    if session.status == 'completed':
        return jsonify({"error": "Session is already completed"}), 400

    session.status = 'completed'
    session.end_time = datetime.now(timezone.utc)

    try:
        db.session.commit()
        return jsonify({
            "message": "Session completed",
            "session": {
                "id": session.id,
                "status": session.status,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat()
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"complete_session failed for session_id={session_id}: {str(e)}")
        return jsonify({"error": "Failed to complete session", "details": str(e)}), 500

@study_bp.route('/study/sessions', methods=['GET'])
@jwt_required()
def list_sessions():
    """List all study sessions for the current user."""
    current_user_id = int(get_jwt_identity())
    query = StudySession.query.filter_by(user_id=current_user_id)

    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter_by(status=status_filter)

    deck_filter = request.args.get('deck_id')
    if deck_filter:
        query = query.filter_by(deck_id=int(deck_filter))

    sessions = query.order_by(StudySession.start_time.desc()).all()

    return jsonify([{
        "id": s.id,
        "deck_id": s.deck_id,
        "deck_title": s.deck.title if s.deck else "Deleted Deck",
        "status": s.status,
        "current_card_index": s.current_card_index,
        "start_time": s.start_time.isoformat(),
        "end_time": s.end_time.isoformat() if s.end_time else None
    } for s in sessions]), 200

# added endpoint to get the review queue for the user,
# THIS endpoint returns a list of flashcards that are due for review based on the spaced repetition algorithm,
# along with their last rating and next review date.
@study_bp.route('/study/review-queue', methods=['GET'])
@jwt_required()
def get_review_queue():
    """Get a list of flashcards that are due for review based on spaced repetition."""
    current_user_id = int(get_jwt_identity())
    now = datetime.now(timezone.utc)

    latest_review_subquery = db.session.query(
        ReviewHistory.flashcard_id,
        func.max(ReviewHistory.reviewed_at).label('latest_review')
    ).filter(
        ReviewHistory.user_id == current_user_id
    ).group_by(
        ReviewHistory.flashcard_id
    ).subquery()

    due_reviews = db.session.query(ReviewHistory).join(
        latest_review_subquery,
        db.and_(
            ReviewHistory.flashcard_id == latest_review_subquery.c.flashcard_id,
            ReviewHistory.reviewed_at == latest_review_subquery.c.latest_review
        )
    ).filter(
        ReviewHistory.user_id == current_user_id,
        ReviewHistory.next_review_date <= now
    )

    deck_filter = request.args.get('deck_id')
    if deck_filter:
        due_reviews = due_reviews.join(Flashcard).filter(
            Flashcard.deck_id == int(deck_filter)
        )

    due_reviews = due_reviews.order_by(ReviewHistory.next_review_date.asc()).all()

    return jsonify([{
        "flashcard_id": review.flashcard_id,
        "question": review.flashcard.question,
        "answer": review.flashcard.answer,
        "deck_id": review.flashcard.deck_id,
        "deck_title": review.flashcard.deck.title if review.flashcard.deck else "Deleted Deck",
        "last_rating": review.rating,
        "next_review_date": review.next_review_date.isoformat(),
        "days_overdue": (now - review.next_review_date).days
    } for review in due_reviews]), 200

@study_bp.route('/study/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """Get high-level study statistics for the user dashboard."""
    current_user_id = int(get_jwt_identity())
    now = datetime.now(timezone.utc)

    total_sessions = StudySession.query.filter_by(
        user_id=current_user_id,
        status='completed'
    ).count()

    total_reviews = ReviewHistory.query.filter_by(user_id=current_user_id).count()

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

    streak = _calculate_study_streak(current_user_id)

    return jsonify({
        "total_sessions": total_sessions,
        "total_cards_reviewed": total_reviews,
        "study_streak": streak,
        "cards_due_today": cards_due or 0
    }), 200

@study_bp.route('/study/analytics/daily', methods=['GET'])
@jwt_required()
def analytics_daily():
    """Get daily review counts for the last X days."""
    current_user_id = int(get_jwt_identity())
    days = request.args.get('days', 30, type=int)
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=days - 1)

    daily_data = db.session.query(
        func.date(ReviewHistory.reviewed_at).label('review_date'),
        func.count(ReviewHistory.id).label('cards_reviewed')
    ).filter(
        ReviewHistory.user_id == current_user_id,
        ReviewHistory.reviewed_at >= start_date
    ).group_by(
        func.date(ReviewHistory.reviewed_at)
    ).all()

    counts_by_date = {str(row.review_date): row.cards_reviewed for row in daily_data}

    result = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        day_str = str(day)
        result.append({
            "date": day_str,
            "cards_reviewed": counts_by_date.get(day_str, 0)
        })

    return jsonify(result), 200

@study_bp.route('/study/analytics/weekly', methods=['GET'])
@jwt_required()
def analytics_weekly():
    """Get weekly review counts for the last X weeks."""
    current_user_id = int(get_jwt_identity())
    weeks = request.args.get('weeks', 12, type=int)
    start_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    weekly_data = db.session.query(
        func.extract('isoyear', ReviewHistory.reviewed_at).label('year'),
        func.extract('week', ReviewHistory.reviewed_at).label('week'),
        func.count(ReviewHistory.id).label('cards_reviewed')
    ).filter(
        ReviewHistory.user_id == current_user_id,
        ReviewHistory.reviewed_at >= start_date
    ).group_by('year', 'week').order_by('year', 'week').all()

    return jsonify([{
        "year": int(row.year),
        "week": int(row.week),
        "cards_reviewed": row.cards_reviewed
    } for row in weekly_data]), 200

@study_bp.route('/study/analytics/monthly', methods=['GET'])
@jwt_required()
def analytics_monthly():
    """Get monthly review counts for the last X months."""
    current_user_id = int(get_jwt_identity())
    months = request.args.get('months', 12, type=int)
    start_date = datetime.now(timezone.utc) - timedelta(days=months * 30)

    monthly_data = db.session.query(
        func.extract('year', ReviewHistory.reviewed_at).label('year'),
        func.extract('month', ReviewHistory.reviewed_at).label('month'),
        func.count(ReviewHistory.id).label('cards_reviewed')
    ).filter(
        ReviewHistory.user_id == current_user_id,
        ReviewHistory.reviewed_at >= start_date
    ).group_by('year', 'month').order_by('year', 'month').all()

    return jsonify([{
        "year": int(row.year),
        "month": int(row.month),
        "cards_reviewed": row.cards_reviewed
    } for row in monthly_data]), 200

@study_bp.route('/study/analytics/top-decks', methods=['GET'])
@jwt_required()
def analytics_top_decks():
    """Get the user's most reviewed decks."""
    current_user_id = int(get_jwt_identity())

    top_decks = db.session.query(
        Deck.id,
        Deck.title,
        func.count(ReviewHistory.id).label('total_reviews')
    ).join(
        Flashcard, ReviewHistory.flashcard_id == Flashcard.id
    ).join(
        Deck, Flashcard.deck_id == Deck.id
    ).filter(
        ReviewHistory.user_id == current_user_id
    ).group_by(
        Deck.id, Deck.title
    ).order_by(
        desc('total_reviews')
    ).limit(5).all()

    return jsonify([{
        "deck_id": row.id,
        "deck_title": row.title,
        "total_reviews": row.total_reviews
    } for row in top_decks]), 200

@study_bp.route('/study/analytics/difficult-cards', methods=['GET'])
@jwt_required()
def analytics_difficult_cards():
    """Get the cards the user most frequently rates as 'hard'."""
    current_user_id = int(get_jwt_identity())

    difficult = db.session.query(
        Flashcard.id,
        Flashcard.question,
        Flashcard.answer,
        Deck.title.label('deck_title'),
        func.count(ReviewHistory.id).label('hard_count')
    ).join(
        Flashcard, ReviewHistory.flashcard_id == Flashcard.id
    ).join(
        Deck, Flashcard.deck_id == Deck.id
    ).filter(
        ReviewHistory.user_id == current_user_id,
        ReviewHistory.rating == 'hard'
    ).group_by(
        Flashcard.id, Flashcard.question, Flashcard.answer, Deck.title
    ).order_by(
        desc('hard_count')
    ).limit(20).all()

    return jsonify([{
        "flashcard_id": row.id,
        "question": row.question,
        "answer": row.answer,
        "deck_title": row.deck_title,
        "hard_count": row.hard_count
    } for row in difficult]), 200

@study_bp.route('/study/analytics/completion', methods=['GET'])
@jwt_required()
def analytics_completion():
    """Get completion percentage for each of the user's decks."""
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)

    created_decks = Deck.query.filter_by(creator_id=current_user_id).all()
    saved_decks = user.saved_decks
    all_decks = list(created_decks) + list(saved_decks)

    completion_data = []
    for deck in all_decks:
        total_cards = Flashcard.query.filter_by(deck_id=deck.id).count()

        if total_cards == 0:
            completion_data.append({
                "deck_id": deck.id,
                "deck_title": deck.title,
                "total_cards": 0,
                "cards_reviewed": 0,
                "completion_pct": 0
            })
            continue

        cards_reviewed = db.session.query(
            func.count(func.distinct(ReviewHistory.flashcard_id))
        ).join(
            Flashcard, ReviewHistory.flashcard_id == Flashcard.id
        ).filter(
            ReviewHistory.user_id == current_user_id,
            Flashcard.deck_id == deck.id
        ).scalar()

        completion_pct = round((cards_reviewed / total_cards) * 100, 1)

        completion_data.append({
            "deck_id": deck.id,
            "deck_title": deck.title,
            "total_cards": total_cards,
            "cards_reviewed": cards_reviewed,
            "completion_pct": completion_pct
        })

    return jsonify(completion_data), 200


#create a helper function to calculate the user's study streak, which is the number of consecutive days (ending today or yesterday) 

def _calculate_study_streak(user_id):
    """Count consecutive days of study activity for a user."""
    # Get all unique dates that the user has reviewed cards..sorting from newest first
    review_dates = db.session.query(
        func.date(ReviewHistory.reviewed_at).label('review_date')
    ).filter(
        ReviewHistory.user_id == user_id
    ).group_by(
        func.date(ReviewHistory.reviewed_at)
    ).order_by(
        func.date(ReviewHistory.reviewed_at).desc()
    ).all()

    if not review_dates:
        return 0

   
    dates = [row.review_date for row in review_dates]
    today = datetime.now(timezone.utc).date()

    # The streak must start from today or yesterday and If the most recent review date is older than yesterday, the streak is broken.
    if dates[0] < today - timedelta(days=1):
        return 0

    # Count consecutive days in reverse .from the most recent review date
    streak = 1
    for i in range(1, len(dates)):
        # If the gap between this date and the previous one is exactly 1 day,
        if dates[i - 1] - dates[i] == timedelta(days=1):
            streak += 1
        else:
            break

    return streak