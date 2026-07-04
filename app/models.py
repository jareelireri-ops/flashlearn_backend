from app import db
from datetime import datetime, timezone
from sqlalchemy.orm import validates

#  USER LEARNING COLLECTIONS
user_collection = db.Table('user_collection',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('deck_id', db.Integer, db.ForeignKey('decks.id', ondelete='CASCADE'), primary_key=True)
)

# 1. USERS
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='learner') 
    
    # i USE TEXT FOR THE P.P  URL since we shall be using base64 uploading format,which will have quite a long string
    name = db.Column(db.String(100), nullable=True)
    profile_picture_url = db.Column(db.Text, nullable=True)
    password_reset_token = db.Column(db.String(255), unique=True, nullable=True)
    password_reset_expires = db.Column(db.DateTime(timezone=True), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    created_decks = db.relationship('Deck', backref='creator', lazy=True)
    saved_decks = db.relationship('Deck', secondary=user_collection, backref=db.backref('learners', lazy='dynamic'))
    study_sessions = db.relationship('StudySession', backref='user', lazy=True, cascade="all, delete-orphan")
    review_history = db.relationship('ReviewHistory', backref='user', lazy=True, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', backref='user', lazy=True)
    reports_made = db.relationship('Report', backref='reporter', lazy=True)

    @validates('email')
    def normalize_email(self, key, value):
        return value.strip().lower() if value else value

    __table_args__ = (
        db.CheckConstraint("role IN ('learner', 'admin')", name='ck_users_role'),
    )

# 2. DECKS
class Deck(db.Model):
    __tablename__ = 'decks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=True)
    tags = db.Column(db.String(200), nullable=True)
    is_public = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    difficulty_level = db.Column(db.String(20), nullable=True)
    
    # creating the foreign key relationship to the users table, ensuring that each deck is associated with a creator
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    flashcards = db.relationship('Flashcard', backref='deck', lazy=True, cascade="all, delete-orphan")
    study_sessions = db.relationship('StudySession', backref='deck', lazy=True, cascade="all, delete-orphan")
    reports = db.relationship('Report', backref='reported_deck', lazy=True, passive_deletes=True)

    __table_args__ = (
        db.CheckConstraint("difficulty_level IS NULL OR difficulty_level IN ('easy', 'medium', 'hard')", name='ck_decks_difficulty'),
    )

# 3. FLASHCARDS
class Flashcard(db.Model):
    __tablename__ = 'flashcards'
    id = db.Column(db.Integer, primary_key=True)
    
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id', ondelete='CASCADE'), nullable=False)
    
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    difficulty_level = db.Column(db.String(20), default='medium')
    image_url = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    reviews = db.relationship('ReviewHistory', backref='flashcard', lazy=True, cascade="all, delete-orphan")
    reports = db.relationship('Report', backref='reported_flashcard', lazy=True, passive_deletes=True)

    __table_args__ = (
        db.CheckConstraint("difficulty_level IN ('easy', 'medium', 'hard')", name='ck_flashcards_difficulty'),
    )

# 5. STUDY SESSIONS
class StudySession(db.Model):
    __tablename__ = 'study_sessions'
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id', ondelete='CASCADE'), nullable=False)
    
    status = db.Column(db.String(20), default='in-progress') 
    
    # this field tracks the index of the current flashcard being studied in the session, allowing for resuming and progress tracking
    current_card_index = db.Column(db.Integer, default=0, nullable=False)
    
    start_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.CheckConstraint("status IN ('in-progress', 'paused', 'completed')", name='ck_study_sessions_status'),
    )

# 6. REVIEW HISTORY
class ReviewHistory(db.Model):
    __tablename__ = 'review_history'
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    flashcard_id = db.Column(db.Integer, db.ForeignKey('flashcards.id', ondelete='CASCADE'), nullable=False)
    
    session_id = db.Column(db.Integer, db.ForeignKey('study_sessions.id', ondelete='SET NULL'), nullable=True)
    session = db.relationship('StudySession', backref='reviews', lazy=True)

    rating = db.Column(db.String(20), nullable=False) 
    reviewed_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    next_review_date = db.Column(db.DateTime(timezone=True), nullable=False)

    __table_args__ = (
        db.CheckConstraint("rating IN ('easy', 'medium', 'hard')", name='ck_review_history_rating'),
    )

# 7. NOTIFICATIONS
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    notification_type = db.Column(db.String(30), nullable=True) 
    related_deck_id = db.Column(db.Integer, db.ForeignKey('decks.id', ondelete='SET NULL'), nullable=True)
    related_flashcard_id = db.Column(db.Integer, db.ForeignKey('flashcards.id', ondelete='SET NULL'), nullable=True)

    related_deck = db.relationship('Deck', foreign_keys=[related_deck_id], backref=db.backref('notifications', passive_deletes=True))
    related_flashcard = db.relationship('Flashcard', foreign_keys=[related_flashcard_id], backref=db.backref('notifications', passive_deletes=True))

# 8. REPORTS
class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id', ondelete='SET NULL'), nullable=True)
    flashcard_id = db.Column(db.Integer, db.ForeignKey('flashcards.id', ondelete='SET NULL'), nullable=True)

    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending') 
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.CheckConstraint("status IN ('pending', 'reviewed', 'resolved')", name='ck_reports_status'),
    )