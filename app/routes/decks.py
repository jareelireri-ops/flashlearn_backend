from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func 
from datetime import datetime, timezone
from app import db
from app.models import User, Deck, Flashcard
from app.routes.notifications import create_notification

# Initialize the Decks Blueprint
decks_bp = Blueprint('decks', __name__)


# this decorator ensures only users with ajwt token can access the CRUD operations for decks and flashcards, 
# and it also allows us to identify the current user making the request WHICH ENFORCES THE BUSINESS RULES guarding deck/f.c management
@decks_bp.route('/decks', methods=['POST'])
@jwt_required()
def create_deck():
    """Create a new deck of flashcards."""
    current_user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    
    # Deck title is strictly required when creating a new deck.
    if 'title' not in data or not data['title'].strip():
        return jsonify({"error": "Deck title cannot be empty"}), 400
      
      
      # we use strip all along when cereating the new deck, to remove any blank spaces to maintain consistency with db
    new_deck = Deck(
        title=data['title'].strip(),
        description=data.get('description', '').strip(),
        category=data.get('category', '').strip(),
        tags=data.get('tags', '').strip(),
        is_public=data.get('is_public', False),
        is_archived=False,
        difficulty_level=data.get('difficulty_level'), # Easy, medium, hard
        creator_id=current_user_id
    )
    
    try:
        db.session.add(new_deck)
        db.session.commit()
        return jsonify({
            "message": "Deck created successfully",
            "deck": {
                "id": new_deck.id,
                "title": new_deck.title,
                "is_public": new_deck.is_public
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create deck", "details": str(e)}), 500
    
    


@decks_bp.route('/decks', methods=['GET'])
@jwt_required()
def get_user_decks():
    """Retrieve all decks created by the logged-in user."""
    current_user_id = int(get_jwt_identity())
    
    user_decks_query = Deck.query.filter_by(creator_id=current_user_id)

    # pagination logic: allows users to navigate through large sets of decks without overwhelming the response.
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    pagination = user_decks_query.paginate(page=page, per_page=per_page, error_out=False)
    user_decks = pagination.items


    return jsonify({
        "decks": [{
            "id": deck.id,
            "title": deck.title,
            "description": deck.description,
            "category": deck.category,
            "tags": deck.tags,
            "is_public": deck.is_public,
            "is_archived": deck.is_archived,
            "difficulty_level": deck.difficulty_level,
            "created_at": deck.created_at
        } for deck in user_decks],
      #pagination metadata to help the frontend manage large sets of decks and navigate through them efficiently.
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next
     
    }), 200


@decks_bp.route('/decks/<int:deck_id>', methods=['GET'])
@jwt_required()
def get_deck_details(deck_id):
    """Get details of a specific deck (must be public OR owned/saved by user)."""
    current_user_id = int(get_jwt_identity())
    deck = db.session.get(Deck, deck_id)
    
    if not deck:
        return jsonify({"error": "Deck not found"}), 404
        
    # Security check if user is allowed to view this deck
    user = db.session.get(User, current_user_id)
    is_saved = deck in user.saved_decks
    
    if not deck.is_public and deck.creator_id != current_user_id and not is_saved:
        return jsonify({"error": "You do not have permission to view this deck"}), 403
        
    return jsonify({
        "id": deck.id,
        "title": deck.title,
        "description": deck.description,
        "category": deck.category,
        "tags": deck.tags,
        "is_public": deck.is_public,
        "is_archived": deck.is_archived,
        "difficulty_level": deck.difficulty_level,
        "creator": deck.creator.name if deck.creator else "Unknown",
        "num_flashcards": len(deck.flashcards),
        "num_learners": deck.learners.count()
    }), 200


@decks_bp.route('/decks/<int:deck_id>', methods=['PUT'])
@jwt_required()
def update_deck(deck_id):
    """Edit deck details (restricted to the creator)."""
    current_user_id = int(get_jwt_identity())
    deck = db.session.get(Deck, deck_id)
    
    if not deck:
        return jsonify({"error": "Deck not found"}), 404
        
    # users can only edit decks they personally created not what they saved from the library.
    if deck.creator_id != current_user_id:
        return jsonify({"error": "Unauthorized to modify this deck"}), 403
        
    data = request.get_json() or {}
    
    if 'title' in data:
        if not data['title'].strip():
            return jsonify({"error": "Deck title cannot be empty"}), 400
        deck.title = data['title'].strip()
        
    if 'description' in data:
        deck.description = data['description'].strip()
    if 'category' in data:
        deck.category = data['category'].strip()
    if 'tags' in data:
        deck.tags = data['tags'].strip()
    if 'is_public' in data:
        deck.is_public = data['is_public']
    if 'is_archived' in data:
        deck.is_archived = data['is_archived']
    if 'difficulty_level' in data:
        deck.difficulty_level = data['difficulty_level']
        
    try:
        db.session.commit()
        return jsonify({"message": "Deck updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update deck", "details": str(e)}), 500


@decks_bp.route('/decks/<int:deck_id>', methods=['DELETE'])
@jwt_required()
def delete_deck(deck_id):
    """Delete a deck (restricted to the creator)."""
    current_user_id = int(get_jwt_identity())
    deck = db.session.get(Deck, deck_id)
    
    if not deck:
        return jsonify({"error": "Deck not found"}), 404
        
    # Authorization check
    if deck.creator_id != current_user_id:
        return jsonify({"error": "Unauthorized to delete this deck"}), 403
        
    try:
        db.session.delete(deck)
        db.session.commit()
        return jsonify({"message": "Deck deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete deck", "details": str(e)}), 500



# Flashcard mgt routes(restricted to the deck owner)


@decks_bp.route('/decks/<int:deck_id>/flashcards', methods=['POST'])
@jwt_required()
def add_flashcard(deck_id):
    """Add a flashcard to a specific deck (restricted to deck owner)."""
    current_user_id = int(get_jwt_identity())
    deck = db.session.get(Deck, deck_id)
    
    if not deck:
        return jsonify({"error": "Deck not found"}), 404
        
    # verify that a user is the creator of the deck before they get permision to add flashcards to it.
    if deck.creator_id != current_user_id:
        return jsonify({"error": "Unauthorized to edit this deck"}), 403
        
    data = request.get_json() or {}
    
    # each flash card must have a question and answer before it can be added to a deck.
    if 'question' not in data or not data['question'].strip():
        return jsonify({"error": "Question field is required"}), 400
    if 'answer' not in data or not data['answer'].strip():
        return jsonify({"error": "Answer field is required"}), 400
        
    new_card = Flashcard(
        deck_id=deck_id,
        question=data['question'].strip(),
        answer=data['answer'].strip(),
        difficulty_level=data.get('difficulty_level', 'medium'),
        image_url=data.get('image_url')
    )

    # ensure "new cards added" is detectable on the frontend,
   
    deck.updated_at = datetime.now(timezone.utc)
    
    try:
        db.session.add(new_card)
        db.session.commit()
        return jsonify({
            "message": "Flashcard added successfully",
            "flashcard_id": new_card.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add flashcard", "details": str(e)}), 500


@decks_bp.route('/decks/<int:deck_id>/flashcards', methods=['GET'])
@jwt_required()
def get_deck_flashcards(deck_id):
    """Get all flashcards in a deck (must have access permission)."""
    current_user_id = int(get_jwt_identity())
    deck = db.session.get(Deck, deck_id)
    
    if not deck:
        return jsonify({"error": "Deck not found"}), 404
        
    # check if user has permisiion to view deck with the given if condtions.
    user = db.session.get(User, current_user_id)
    is_saved = deck in user.saved_decks
    
    if not deck.is_public and deck.creator_id != current_user_id and not is_saved:
        return jsonify({"error": "Permission denied"}), 403
        
    cards_query = Flashcard.query.filter_by(deck_id=deck_id)

   #pagination logic: allows users to navigate through large sets of flashcards without overwhelming the response.
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    pagination = cards_query.paginate(page=page, per_page=per_page, error_out=False)
    cards = pagination.items
  

    return jsonify({
        "flashcards": [{
            "id": card.id,
            "question": card.question,
            "answer": card.answer,
            "difficulty_level": card.difficulty_level,
            "image_url": card.image_url
        } for card in cards],
       
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next
       
    }), 200


@decks_bp.route('/flashcards/<int:card_id>', methods=['PUT'])
@jwt_required()
def update_flashcard(card_id):
    """Edit flashcard details (restricted to deck owner)."""
    current_user_id = int(get_jwt_identity())
    card = db.session.get(Flashcard, card_id)
    
    if not card:
        return jsonify({"error": "Flashcard not found"}), 404
        
    # only the creator of a deck can edit the cards in the deck, ensures saved decks cant be modified just cause you saved them to your collection
    if card.deck.creator_id != current_user_id:
        return jsonify({"error": "Unauthorized to modify this card"}), 403
        
    data = request.get_json() or {}
    
    if 'question' in data:
        if not data['question'].strip():
            return jsonify({"error": "Question cannot be empty"}), 400
        card.question = data['question'].strip()
        
    if 'answer' in data:
        if not data['answer'].strip():
            return jsonify({"error": "Answer cannot be empty"}), 400
        card.answer = data['answer'].strip()
        
    if 'difficulty_level' in data:
        card.difficulty_level = data['difficulty_level']
    if 'image_url' in data:
        card.image_url = data['image_url']
        
    try:
        db.session.commit()
        return jsonify({"message": "Flashcard updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update flashcard", "details": str(e)}), 500


@decks_bp.route('/flashcards/<int:card_id>', methods=['DELETE'])
@jwt_required()
def delete_flashcard(card_id):
    """Delete a flashcard (restricted to deck owner)."""
    current_user_id = int(get_jwt_identity())
    card = db.session.get(Flashcard, card_id)
    
    if not card:
        return jsonify({"error": "Flashcard not found"}), 404
        
    # only creator of deck can delete the cards, not the users who save dthem to their collection.
    if card.deck.creator_id != current_user_id:
        return jsonify({"error": "Unauthorized to delete this card"}), 403
        
    try:
        db.session.delete(card)
        db.session.commit()
        return jsonify({"message": "Flashcard deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete flashcard", "details": str(e)}), 500


# public routes for landing page


@decks_bp.route('/public/categories', methods=['GET'])
def get_public_categories():
    """Return all distinct categories that have at least one public deck ."""
    results = db.session.query(
        Deck.category,
        func.count(Deck.id).label('deck_count')
    ).filter(
        Deck.is_public == True,
        Deck.is_archived == False,
        Deck.category != None,
        Deck.category != ''
    ).group_by(Deck.category).order_by(Deck.category).all()
    return jsonify([{
        "category": row.category,
        "deck_count": row.deck_count
    } for row in results]), 200

@decks_bp.route('/public/decks', methods=['GET'])
def get_public_decks():
    """Browse public decks without authentication — for guests on the page.
    Supports ?category= and ?search= filters. Returns deck info but not all flashcards content."""
    query = Deck.query.filter_by(is_public=True, is_archived=False)
    
    category = request.args.get('category')
    if category:
        query = query.filter_by(category=category)
        
    keyword = request.args.get('search')
    if keyword:
        query = query.filter(
            (Deck.title.ilike(f'%{keyword}%')) |
            (Deck.description.ilike(f'%{keyword}%'))
        )
        
    difficulty = request.args.get('difficulty')
    if difficulty:
        query = query.filter(Deck.difficulty_level == difficulty)
 
    #  PAGINATION
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    decks = pagination.items
   

    return jsonify({
        "decks": [{
            "id": deck.id,
            "title": deck.title,
            "description": deck.description,
            "category": deck.category,
            "difficulty_level": deck.difficulty_level,
            "creator": deck.creator.name if deck.creator else "Unknown",
            "num_flashcards": len(deck.flashcards),
            "num_learners": deck.learners.count(),
            "created_at": deck.created_at.isoformat(),
            "updated_at": deck.updated_at.isoformat()
        } for deck in decks],
      
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next
      
    }), 200
  
  # route for deckdrawer before a studysession is intialized  
@decks_bp.route('/decks/<int:deck_id>/preview', methods=['GET'])
def get_deck_preview(deck_id):
    """Public teaser: returns only the first card's question for a public deck.
    No auth required. Never exposes the answer or other cards."""
    deck = db.session.get(Deck, deck_id)

    if not deck:
        return jsonify({"error": "Deck not found"}), 404

    if not deck.is_public or deck.is_archived:
        return jsonify({"error": "This deck is not available"}), 403

    first_card = Flashcard.query.filter_by(deck_id=deck_id).order_by(Flashcard.id.asc()).first()

    return jsonify({
        "deck_id": deck.id,
        "first_question": first_card.question if first_card else None
    }), 200

# PERSONAL LEARNING COLLECTION ROUTES

@decks_bp.route('/collection', methods=['GET'])
@jwt_required()
def get_collection():
    """Retrieve all decks in the user's study collection (created + saved public decks)."""
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    
    # All decks created by the user
    created_decks = Deck.query.filter_by(creator_id=current_user_id).all()
    
    # All public decks saved by the user
    saved_decks = user.saved_decks
    
    collection = []
    
    # Add created decks
    for deck in created_decks:
        collection.append({
            "id": deck.id,
            "title": deck.title,
            "description": deck.description,
            "category": deck.category,
            "difficulty_level": deck.difficulty_level,
            "is_owner": True,
            "num_flashcards": len(deck.flashcards),
            "created_at": deck.created_at.isoformat(),
            "updated_at": deck.updated_at.isoformat()
        })
        
    # Add saved decks
    for deck in saved_decks:
        collection.append({
            "id": deck.id,
            "title": deck.title,
            "description": deck.description,
            "category": deck.category,
            "difficulty_level": deck.difficulty_level,
            "is_owner": False,
            "num_flashcards": len(deck.flashcards),
            "created_at": deck.created_at.isoformat(),
            "updated_at": deck.updated_at.isoformat()
        })

    # PAGINATION LOGIC
    # created_decks and saved_decks are combined into a single collection,
    # its then paginated based on the page and per_page query parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    total = len(collection)
    start = (page - 1) * per_page
    end = start + per_page
    paginated_collection = collection[start:end]

    return jsonify({
        "collection": paginated_collection,
        "page": page,
        "per_page": per_page,
        "total": total,
        "pages": (total + per_page - 1) // per_page,
        "has_next": end < total
    }), 200
  #this returns the decks in the user's collection, both created and saved public decks, with pagination support.


@decks_bp.route('/collection/add/<int:deck_id>', methods=['POST'])
@jwt_required()
def add_to_collection(deck_id):
    """Add a public deck to the user's saved collections."""
    current_user_id = int(get_jwt_identity())
    deck = db.session.get(Deck, deck_id)
    
    if not deck:
        return jsonify({"error": "Deck not found"}), 404
        
    # user cannot save their own deck
    if deck.creator_id == current_user_id:
        return jsonify({"error": "You already own this deck"}), 400
        
    # Only public decks can be added to collections
    if not deck.is_public:
        return jsonify({"error": "Cannot add private decks to collection"}), 403
        
    user = db.session.get(User, current_user_id)
    
    # Do not duplicate if already saved
    if deck in user.saved_decks:
        return jsonify({"message": "Deck is already in your collection"}), 200
        
    try:
        user.saved_decks.append(deck)
        create_notification(
            user_id=current_user_id,
            message=f'"{deck.title}" was added to your collection.',
            notification_type='collection_added',
            related_deck_id=deck.id
        )
        db.session.commit()
        return jsonify({"message": "Deck added to collection successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to add to collection", "details": str(e)}), 500


@decks_bp.route('/collection/remove/<int:deck_id>', methods=['DELETE'])
@jwt_required()
def remove_from_collection(deck_id):
    """Remove a saved public deck from the user's collection."""
    current_user_id = int(get_jwt_identity())
    deck = db.session.get(Deck, deck_id)
    
    if not deck:
        return jsonify({"error": "Deck not found"}), 404
        
    user = db.session.get(User, current_user_id)
    
    if deck not in user.saved_decks:
        return jsonify({"error": "Deck is not in your collection"}), 400
        
    try:
        user.saved_decks.remove(deck)
        db.session.commit()
        return jsonify({"message": "Deck removed from collection successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to remove from collection", "details": str(e)}), 500