import os
from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User, Deck, Flashcard

app = create_app()

def seed_database():
    with app.app_context():
        db.drop_all()
        db.create_all()

        print("Creating users...")
        admin = User(
            email="jareelboi@gmail.com",
            password_hash=generate_password_hash("PGBWMA11"),
            role="admin",
            name="FL Admin",
            is_active=True
        )
        
        creator = User(
            email="rabbiflashlearn@gmail.com",
            password_hash=generate_password_hash("password123"),
            role="learner",
            name="Jareel Ireri",
            is_active=True
        )
        
        db.session.add_all([admin, creator])
        db.session.commit()

        print("Populating Decks and Flashcards...")
        
        seed_data = [
            # 1. DATA DESTRUCTION
            {
                "title": "Secure HDD Eradication", "category": "Data Destruction", "level": "medium",
                "desc": "Protocols for DoD standard hard drive wiping and shredding.",
                "cards": [
                    ("What is DoD 5220.22-M?", "A data sanitization method that overwrites data with zeros, ones, and random characters."),
                    ("Why physical shredding?", "It ensures the physical platter is destroyed, making data recovery entirely impossible."),
                    ("What is a Certificate of Destruction (CoD)?", "A legal document verifying that electronic media has been securely destroyed.")
                ]
            },
            {
                "title": "SSD Sanitization", "category": "Data Destruction", "level": "hard",
                "desc": "How to handle Solid State Drives securely.",
                "cards": [
                    ("Why can't you degauss an SSD?", "SSDs use flash memory, not magnetic platters, so degaussing has no effect on them."),
                    ("What is Cryptographic Erasure?", "Deleting the encryption key, rendering the encrypted data on the SSD permanently unreadable."),
                    ("What is ATA Secure Erase?", "A firmware-level command that resets all storage cells on an SSD to empty.")
                ]
            },

            # 2. LITHIUM SAFETY
            {
                "title": "Battery Handling 101", "category": "Lithium Safety", "level": "easy",
                "desc": "Safety protocols for handling swollen or damaged batteries.",
                "cards": [
                    ("What indicates a swollen battery?", "The casing of the device is bulging, or the trackpad is lifting."),
                    ("What should you NEVER do to a swollen battery?", "Puncture, bend, or apply pressure to it, as it can cause a thermal runaway fire."),
                    ("Where should damaged batteries be stored?", "In a fireproof sand bucket or specialized battery containment unit.")
                ]
            },

            # 3. ESG COMPLIANCE
            {
                "title": "Corporate ESG Basics", "category": "ESG Compliance", "level": "easy",
                "desc": "Understand Environmental, Social, and Governance reporting.",
                "cards": [
                    ("What does ESG stand for?", "Environmental, Social, and Governance."),
                    ("How does E-Waste recycling improve the 'E' in ESG?", "It reduces landfill toxic leakage and lowers the carbon footprint by reusing precious metals."),
                    ("What is Scope 3 emissions?", "Indirect emissions that occur in a company's value chain, including employee electronic waste.")
                ]
            },
            {
                "title": "Circular Economy", "category": "ESG Compliance", "level": "medium",
                "desc": "Moving from a linear to a circular IT lifecycle.",
                "cards": [
                    ("What is a Circular Economy?", "An economic model focused on minimizing waste and making the most of resources by keeping them in use as long as possible."),
                    ("What is ITAD?", "IT Asset Disposition - the safe and ecologically responsible disposal of corporate IT equipment."),
                    ("How does refurbishment help developing nations?", "It bridges the digital divide by providing affordable, high-quality technology to schools and communities.")
                ]
            },

            # 4. ASSET RECOVERY
            {
                "title": "Grading Refurbished Laptops", "category": "Asset Recovery", "level": "medium",
                "desc": "Industry standards for cosmetic and functional grading.",
                "cards": [
                    ("What is Grade A condition?", "Like-new condition with minimal to no scuffs or scratches."),
                    ("What is Grade C condition?", "Significant cosmetic damage, deep scratches, but functionally operational."),
                    ("What components are tested during triage?", "Battery health, keyboard, screen pixels, and I/O ports.")
                ]
            },

            # 5. DEVICE TEARDOWNS
            {
                "title": "MacBook Teardown Safety", "category": "Device Teardowns", "level": "hard",
                "desc": "Protocols for disassembling Apple laptops.",
                "cards": [
                    ("What is the first step before disassembling a laptop?", "Disconnect the internal battery to prevent short circuits."),
                    ("Why must you use an anti-static wrist strap?", "To prevent Electrostatic Discharge (ESD) from damaging the motherboard components."),
                    ("What tool is required for Apple pentalobe screws?", "A P5 pentalobe screwdriver.")
                ]
            }
        ]

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
            db.session.flush()

            for q, a in d_data["cards"]:
                card = Flashcard(
                    deck_id=deck.id,
                    question=q,
                    answer=a,
                    difficulty_level=d_data["level"]
                )
                db.session.add(card)

        db.session.commit()
        print("Database successfully seeded!.")

if __name__ == "__main__":
    seed_database()