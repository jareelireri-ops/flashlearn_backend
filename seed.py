import os
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User, Deck, Flashcard

app = create_app()

def seed_database():
    with app.app_context():
        print("Clearing database...")
        db.drop_all()
        db.create_all()

        print("Creating users...")
        admin = User(
            email="admin@flashlearn.com",
            password_hash=generate_password_hash("admin123"),
            role="admin",
            name="FL Admin",
            is_active=True
        )
        
        creator = User(
            email="rabbiflashlearn.com",
            password_hash=generate_password_hash("password123"),
            role="learner",
            name="Jareel Ireri",
            is_active=True
        )
        
        db.session.add_all([admin, creator])
        db.session.commit()

        print("Populating Decks and Flashcards...")
        
        # SEED DATA STRUCTURE 
        seed_data = [
            # 1. SOFTWARE ENGINEERING
            {
                "title": "JavaScript Basics", "category": "Software Engineering", "level": "medium",
                "desc": "Master the core concepts of JavaScript, closures, and the DOM.",
                "cards": [
                    ("What is a closure?", "A function bundled with its lexical environment."),
                    ("What does 'use strict' do?", "Enforces stricter parsing and error handling in JS code."),
                    ("What is the DOM?", "Document Object Model - an interface for web documents.")
                ]
            },
            {
                "title": "Python Basics", "category": "Software Engineering", "level": "easy",
                "desc": "Core syntax and data structures in Python.",
                "cards": [
                    ("What is the difference between a list and a tuple?", "Lists are mutable (can be changed), tuples are immutable."),
                    ("What does the 'yield' keyword do?", "It pauses a function and returns a generator iterator."),
                    ("What is a dictionary?", "A mutable data structure that stores key-value pairs.")
                ]
            },
            {
                "title": "CSS Fundamentals", "category": "Software Engineering", "level": "easy",
                "desc": "Learn how to style the web with modern CSS.",
                "cards": [
                    ("What is Flexbox?", "A one-dimensional layout method for arranging items in rows or columns."),
                    ("Explain the CSS Box Model.", "It consists of margins, borders, padding, and the actual content."),
                    ("What does 'rem' stand for?", "Root 'em' - a unit relative to the font-size of the root element (<html>).")
                ]
            },
            {
                "title": "Artificial Intelligence Concepts", "category": "Software Engineering", "level": "hard",
                "desc": "High-level concepts in AI and Machine Learning.",
                "cards": [
                    ("What is a Neural Network?", "A series of algorithms that endeavors to recognize underlying relationships in a set of data through a process that mimics the way the human brain operates."),
                    ("What is Supervised Learning?", "Training an algorithm on labeled data so it can predict outcomes for unforeseen data."),
                    ("What is an LLM?", "Large Language Model - a deep learning algorithm that can recognize, summarize, translate, predict and generate text.")
                ]
            },

            # 2. BIBLICAL STUDIES
            {
                "title": "New Testament Gospels", "category": "Biblical Studies", "level": "easy",
                "desc": "Key events and figures from the four gospels.",
                "cards": [
                    ("Who are the authors of the four Gospels?", "Matthew, Mark, Luke, and John."),
                    ("What is the Sermon on the Mount?", "A collection of Jesus' teachings and moral sayings, found in Matthew chapters 5, 6, and 7."),
                    ("Where was Jesus born?", "Bethlehem.")
                ]
            },
            {
                "title": "Old Testament Prophets", "category": "Biblical Studies", "level": "medium",
                "desc": "Learn the major and minor prophets of the Old Testament.",
                "cards": [
                    ("Who are the Major Prophets?", "Isaiah, Jeremiah, Lamentations, Ezekiel, and Daniel."),
                    ("What is the central theme of the Book of Jonah?", "God's mercy and compassion extends to all people, even the enemies of Israel."),
                    ("Who led the Israelites out of Egypt?", "Moses.")
                ]
            },
            {
                "title": "Proverbs & Wisdom", "category": "Biblical Studies", "level": "easy",
                "desc": "Wisdom literature and practical teachings.",
                "cards": [
                    ("Who is primarily credited with writing Proverbs?", "King Solomon."),
                    ("According to Proverbs, what is the beginning of wisdom?", "The fear of the Lord."),
                    ("What is a proverb?", "A short, pithy saying stating a general truth or piece of advice.")
                ]
            },

            # 3. PHILOSOPHY
            {
                "title": "Stoicism 101", "category": "Philosophy", "level": "medium",
                "desc": "Ancient wisdom for modern resilience.",
                "cards": [
                    ("What is the core belief of Stoicism?", "We cannot control external events, only our reactions to them."),
                    ("Who was Marcus Aurelius?", "A Roman Emperor and prominent Stoic philosopher, author of 'Meditations'."),
                    ("What is 'Amor Fati'?", "A stoic mindset meaning 'love of fate' - accepting everything that happens in life.")
                ]
            },
            {
                "title": "Existentialism Concepts", "category": "Philosophy", "level": "hard",
                "desc": "Exploring freedom, choice, and meaning.",
                "cards": [
                    ("What does 'existence precedes essence' mean?", "The idea that humans exist first, and then each individual must define their own meaning or essence in life."),
                    ("Who is considered the father of existentialism?", "Søren Kierkegaard."),
                    ("What is 'The Absurd'?", "The conflict between the human tendency to seek inherent value and meaning in life and the silent, meaningless universe.")
                ]
            },

            # 4. BUSINESS MANAGEMENT
            {
                "title": "Agile Methodologies", "category": "Business Management", "level": "medium",
                "desc": "Modern project management for software and beyond.",
                "cards": [
                    ("What is a Sprint?", "A short, time-boxed period when a scrum team works to complete a set amount of work."),
                    ("What is the role of a Scrum Master?", "To facilitate the scrum process, remove impediments, and ensure the team follows agile principles."),
                    ("What is a Kanban board?", "A visual tool used to manage tasks and workflow stages.")
                ]
            },
            {
                "title": "Marketing 101", "category": "Business Management", "level": "easy",
                "desc": "Core principles of marketing and branding.",
                "cards": [
                    ("What are the 4 Ps of Marketing?", "Product, Price, Place, and Promotion."),
                    ("What is a Target Audience?", "The specific group of consumers most likely to want your product or service."),
                    ("What does ROI stand for?", "Return on Investment.")
                ]
            },

            # 5. HOSPITALITY
            {
                "title": "Front Desk Operations", "category": "Hospitality", "level": "easy",
                "desc": "Essential knowledge for hotel front desk agents.",
                "cards": [
                    ("What is a 'Folio'?", "A guest's account or bill maintained by the front desk."),
                    ("What is 'RevPAR'?", "Revenue Per Available Room - a key performance metric in the hotel industry."),
                    ("How should you handle a guest complaint?", "Listen actively, apologize, offer a solution, and follow up.")
                ]
            },
            {
                "title": "Food Safety Standards", "category": "Hospitality", "level": "medium",
                "desc": "Critical knowledge for kitchen and restaurant staff.",
                "cards": [
                    ("What is the 'Danger Zone' for food temperature?", "Between 40°F and 140°F (4°C and 60°C), where bacteria multiply rapidly."),
                    ("What does FIFO stand for?", "First In, First Out - a method of rotating inventory so the oldest stock is used first."),
                    ("What is cross-contamination?", "The physical transfer of harmful bacteria from one person, object, or place to another.")
                ]
            }
        ]

        # insert into db
        for d_data in seed_data:
            deck = Deck(
                title=d_data["title"],
                description=d_data["desc"],
                category=d_data["category"],
                difficulty_level=d_data["level"],
                is_public=True,
                creator_id=creator.id
            )
            db.session.add(deck)
            db.session.flush() # gets the deck ID before committing

            for q, a in d_data["cards"]:
                card = Flashcard(
                    deck_id=deck.id,
                    question=q,
                    answer=a,
                    difficulty_level=d_data["level"]
                )
                db.session.add(card)

        db.session.commit()
        print("Database successfully seeded! Landing page is ready for testing.")

if __name__ == "__main__":
    seed_database()