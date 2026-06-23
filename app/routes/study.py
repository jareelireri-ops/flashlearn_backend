from flask import Blueprint, request, jsonify
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
# This is the same permission logic used in decks.py 

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

    # Verify the user has permission to study this deck
    if not user_can_access_deck(user, deck):
        return jsonify({"error": "You do not have access to this deck"}), 403

    # Check if the deck actually has flashcards to study
    card_count = Flashcard.query.filter_by(deck_id=deck_id).count()
    if card_count == 0:
        return jsonify({"error": "This deck has no flashcards to study"}), 400

    # Prevent duplicate sessions — if user already has an in-progress or paused session
    # for this deck, return that session instead of creating a new one.
    existing_session = StudySession.query.filter_by(
        user_id=current_user_id,
        deck_id=deck_id
    ).filter(
        StudySession.status.in_(['in-progress', 'paused'])
    ).first()

    # we also allow the user to force a new session even if one exists, by sending a JSON payload with {"force_new": true}. 
    # This is useful if they want to start fresh and not continue the previous session. 
    if existing_session:
        data = request.get_json() or {}
        if data.get('force_new'):
            existing_session.status = 'completed'
            existing_session.end_time = datetime.now(timezone.utc)
            db.session.commit()
        else:
            return jsonify({
                "message": "Resuming existing session",
                "session": {
                    "id": existing_session.id,
                    "deck_id": existing_session.deck_id,
                    "status": existing_session.status,
                    "current_card_index": existing_session.current_card_index,
                    "total_cards": card_count,
                    "start_time": existing_session.start_time.isoformat()
                }
            }), 200

    # Create a new study session, starting from the first card
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
        return jsonify({"error": "Failed to start session", "details": str(e)}), 500


@study_bp.route('/study/sessions/<int:session_id>/card', methods=['GET'])
@jwt_required()
def get_current_card(session_id):
    """Get the current flashcard in the study session, with optional forward/backward navigation."""
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

    # Fetch all flashcards in this deck ordered by creation time.
    # We use the card's position in this ordered list as the index,
    # which is what current_card_index tracks (see models.py comment on line 101).
    cards = Flashcard.query.filter_by(
        deck_id=session.deck_id
    ).order_by(Flashcard.created_at).all()

    total_cards = len(cards)

    # If the index is past the last card, the session is complete
    if session.current_card_index >= total_cards:
        db.session.commit()
        return jsonify({
            "session_complete": True,
            "message": "You have reviewed all cards in this deck!",
            "total_cards": total_cards,
            "current_card_index": session.current_card_index
        }), 200

    # Get the card at the current index
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
        return jsonify({"error": "Failed to fetch card", "details": str(e)}), 500


@study_bp.route('/study/sessions/<int:session_id>/review', methods=['POST'])
@jwt_required()
def review_card(session_id):
    """Record a card review with a confidence rating and calculate the next review date."""
    current_user_id = int(get_jwt_identity())
    session = db.session.get(StudySession, session_id)

    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session.user_id != current_user_id:
        return jsonify({"error": "Unauthorized to access this session"}), 403

    if session.status != 'in-progress':
        return jsonify({"error": "Session is not in progress"}), 400

    data = request.get_json() or {}

    if 'flashcard_id' not in data:
        return jsonify({"error": "flashcard_id is required"}), 400

    if 'rating' not in data or data['rating'] not in REVIEW_INTERVALS:
        return jsonify({"error": "Rating must be one of: easy, medium, hard"}), 400

    # Verify the flashcard exists and belongs to the deck being studied
    flashcard = db.session.get(Flashcard, data['flashcard_id'])
    if not flashcard:
        return jsonify({"error": "Flashcard not found"}), 404

    if flashcard.deck_id != session.deck_id:
        return jsonify({"error": "This flashcard does not belong to the current study deck"}), 400

    # Calculate the next review date using spaced repetition intervals.
    # The date is always calculated from NOW, not from any previous due date.
    # This means if a user reviews an overdue card, the interval starts fresh from today.
    rating = data['rating']
    now = datetime.now(timezone.utc)
    next_review = now + REVIEW_INTERVALS[rating]

    # Create the review history record
    review = ReviewHistory(
        user_id=current_user_id,
        flashcard_id=flashcard.id,
        session_id=session.id,
        rating=rating,
        reviewed_at=now,
        next_review_date=next_review
    )

    # Advance the card index so the next call to /card returns the following card
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
        return jsonify({"error": "Failed to record review", "details": str(e)}), 500


@study_bp.route('/study/sessions/<int:session_id>/pause', methods=['PUT'])
@jwt_required()
def pause_session(session_id):
    """Pause an in-progress study session so the user can come back later."""
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
        return jsonify({"error": "Failed to pause session", "details": str(e)}), 500


@study_bp.route('/study/sessions/<int:session_id>/resume', methods=['PUT'])
@jwt_required()
def resume_session(session_id):
    """Resume a paused study session from where the user left off."""
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
        return jsonify({"message": "Session resumed", "current_card_index": session.current_card_index}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to resume session", "details": str(e)}), 500


@study_bp.route('/study/sessions/<int:session_id>/complete', methods=['PUT'])
@jwt_required()
def complete_session(session_id):
    """Mark a study session as completed and record the end time."""
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
        return jsonify({"error": "Failed to complete session", "details": str(e)}), 500


@study_bp.route('/study/sessions', methods=['GET'])
@jwt_required()
def list_sessions():
    """List all study sessions for the current user, with optional status and deck filters."""
    current_user_id = int(get_jwt_identity())

    query = StudySession.query.filter_by(user_id=current_user_id)

    # Optional filters so the frontend can show e.g. only paused sessions
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



# SPACED REPETITION REVIEW QUEUE TO GET DUE CARDS 

# This is the heart of the spaced repetition system.
# It returns flashcards that are DUE for review — their next_review_date has passed.
# Hard-rated cards come back after 1 day, so they naturally appear here more often
# than easy-rated cards (7 days). That's how difficult cards surface more frequently.


@study_bp.route('/study/review-queue', methods=['GET'])
@jwt_required()
def get_review_queue():
    """Get all flashcards that are due for review based on spaced repetition scheduling."""
    current_user_id = int(get_jwt_identity())
    now = datetime.now(timezone.utc)

    # We need the LATEST review for each flashcard (a card may have been reviewed
    # multiple times). We use a subquery to find the most recent review per flashcard,
    # then filter to only those where next_review_date has passed.
    latest_review_subquery = db.session.query(
        ReviewHistory.flashcard_id,
        func.max(ReviewHistory.reviewed_at).label('latest_review')
    ).filter(
        ReviewHistory.user_id == current_user_id
    ).group_by(
        ReviewHistory.flashcard_id
    ).subquery()

    # Join to get the actual ReviewHistory rows, then filter by due date
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

    # Optional filter to get due cards for a specific deck only. BECAUSE a user may have multiple decks, the frontend can request due cards for one deck at a time.
    deck_filter = request.args.get('deck_id')
    if deck_filter:
        due_reviews = due_reviews.join(Flashcard).filter(
            Flashcard.deck_id == int(deck_filter)
        )

    # Order by most overdue first — cards that have been waiting the longest appear at the top
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



# USER LEARNING ANALYTICS TO PROVIDE INSIGHTS ON THEIR STUDY HABITS

# All analytics endpoints query the ReviewHistory and StudySession tables
# for the current user and return data formatted for frontend charts and dashboards. 
# This includes total sessions, streaks, cards due, and performance.


@study_bp.route('/study/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """Get an overview of the user's study activity: total sessions, reviews, streak, cards due."""
    current_user_id = int(get_jwt_identity())
    now = datetime.now(timezone.utc)

    # Count total completed study sessions
    total_sessions = StudySession.query.filter_by(
        user_id=current_user_id,
        status='completed'
    ).count()

    # Count total card reviews ever made
    total_reviews = ReviewHistory.query.filter_by(user_id=current_user_id).count()

    # Count cards that are currently due for review (next_review_date <= now)
    # We only count the latest review per flashcard (same subquery logic as review queue)
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

    # Calculate study streak — consecutive days ending today (or yesterday) with at least 1 review
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
    """Get the number of cards reviewed per day for charting. Defaults to last 30 days."""
    current_user_id = int(get_jwt_identity())
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Group reviews by date and count them
    daily_data = db.session.query(
        func.date(ReviewHistory.reviewed_at).label('review_date'),
        func.count(ReviewHistory.id).label('cards_reviewed')
    ).filter(
        ReviewHistory.user_id == current_user_id,
        ReviewHistory.reviewed_at >= start_date
    ).group_by(
        func.date(ReviewHistory.reviewed_at)
    ).order_by(
        func.date(ReviewHistory.reviewed_at)
    ).all()

    return jsonify([{
        "date": str(row.review_date),
        "cards_reviewed": row.cards_reviewed
    } for row in daily_data]), 200


@study_bp.route('/study/analytics/weekly', methods=['GET'])
@jwt_required()
def analytics_weekly():
    """Get cards reviewed per week for the past 12 weeks."""
    current_user_id = int(get_jwt_identity())
    weeks = request.args.get('weeks', 12, type=int)
    start_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)

    # grouping the reviews by the week of the year(isoyear) and counting how many reviews were done in each week
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
    """Get cards reviewed per month for the past 12 months."""
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
    """Get the user's top 5 most studied decks ranked by total reviews."""
    current_user_id = int(get_jwt_identity())

    # Join ReviewHistory → Flashcard → Deck to count reviews per deck
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
    """Get the flashcards the user struggles with most, ranked by number of 'hard' ratings."""
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
    """Get completion percentages for each deck in the user's collection."""
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)

    # Gather all decks the user has access to (created + saved)
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

        # Count how many UNIQUE flashcards in this deck the user has reviewed at least once
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


#we create a helper function to calculate the user's study streak, which is the number of consecutive days (ending today or yesterday) 
# where the user completed at least one review.

#the function to calculate study streak how many days they did in a row.


def _calculate_study_streak(user_id):
    """Count consecutive days of study activity for a user."""
    # Get all distinct dates the user has reviewed cards, sorted newest first
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

    # Convert to a list of date objects
    dates = [row.review_date for row in review_dates]
    today = datetime.now(timezone.utc).date()

    # The streak must start from today or yesterday.
    # If the most recent review date is older than yesterday, the streak is broken.
    if dates[0] < today - timedelta(days=1):
        return 0

    # Count consecutive days walking backward from the most recent review date
    streak = 1
    for i in range(1, len(dates)):
        # If the gap between this date and the previous one is exactly 1 day, the streak continues
        if dates[i - 1] - dates[i] == timedelta(days=1):
            streak += 1
        else:
            # Gap is bigger than 1 day — streak is broken
            break

    return streak