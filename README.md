# FlashLearn — Backend

This is the backend API for FlashLearn. It handles user authentication, tracks study history, calculates spaced repetition schedules, and manages content reports for admins.

* **Live API:** https://flashlearn-backend-ocnv.onrender.com
* **Frontend App:** https://flashlearn-frontend-ten.vercel.app

---

## Database Design Notes

A few decisions here aren't obvious from the models alone, so worth explaining:

**Shared decks don't get copied**
When a user adds a public deck to their library, we don't duplicate the deck's rows. We just add an entry to a join table (`user_collection`) linking the user to the original deck. If the original creator fixes a typo or edits a card, everyone who has that deck sees the update immediately — there's nothing to keep in sync.

**Deleting a creator's account doesn't delete their decks**
If a user who created a popular public deck deletes their account, we don't want that to break the deck for everyone else studying it. So instead of cascading the delete, we just remove the link to that user's ID and leave the deck itself in place. Students keep their progress either way.

**Flashcards are separate from personal progress**
A flashcard row only holds the question and answer. Review scores and scheduling live in their own table (`ReviewHistory`), tied to the user, not the card. That's what lets a few thousand people study the same public deck at once without their review histories overlapping.

Spaced repetition logic:
- **Easy** → card comes back in 7 days
- **Medium** → card comes back in 3 days
- **Hard** → card comes back tomorrow

**Ownership checks and admin access**
Before letting someone edit or delete a card, the backend checks whether they're the creator. If not, the request is blocked. Admin-only routes (content reports, suspending accounts) are gated behind an `admin` role check.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language/Framework | Python, Flask |
| Database | PostgreSQL, SQLAlchemy, Flask-Migrate |
| Auth | Flask-JWT-Extended |
| Deployment | Gunicorn, Procfile |

---

## Project Structure

```text
flashlearn_backend/
├── app/
│   ├── routes/
│   │   ├── admin.py          # Moderation and user controls
│   │   ├── auth.py           # Signup, login, profile updates
│   │   ├── decks.py          # Deck creation, updates, library search
│   │   ├── notifications.py  # Review reminders and alerts
│   │   └── study.py          # Card reviews and session tracking
│   ├── __init__.py           # App factory and config
│   └── models.py             # Database models
├── migrations/                # Alembic migration history
├── API.md                     # Endpoint documentation
├── config.py                  # Config loader
├── FLASHLEARN_ERD.png          # Database ER diagram
├── Procfile                    # Production start command
├── requirements.txt             # Python dependencies
├── run.py                      # App entrypoint
├── seed.py                     # Local dev seed script
├── test_api.py                  # Test suite
└── update_admin.py              # Script to update admin users
```

---

## Getting Started

### Local Setup

**1. Clone the repository**
```bash
git clone https://github.com/jareelireri-ops/flashlearn_backend.git
cd flashlearn_backend
```

**2. Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up environment variables**

```bash
cp .env.example .env
```
Fill in `DATABASE_URL`, `SECRET_KEY`, and `JWT_SECRET_KEY` in the new `.env` file.

**5. Set up the database**
```bash
flask db upgrade
python seed.py
```

**6. Run the server**
```bash
flask run
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Connection string for the PostgreSQL database |
| `SECRET_KEY` | Flask secret key for session/request security |
| `JWT_SECRET_KEY` | Secret used to sign and verify JWT tokens |
| `CORS_ORIGINS` | Allowed frontend origin(s) for CORS |

---

## Related Repositories
- [Frontend Client Repository](https://flashlearn-frontend-ten.vercel.app)
