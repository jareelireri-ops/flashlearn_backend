# FlashLearn — Backend

REST API for the FlashLearn platform. Handles authentication, deck and flashcard management, study sessions, spaced repetition logic, analytics, notifications, and admin operations.

**Live API:** https://flashlearn-backend-ocnv.onrender.com  
**Frontend App:** https://flashlearn-frontend-ten.vercel.app

---

## Tech Stack

- Python / Flask
- PostgreSQL
- SQLAlchemy ORM
- Flask-Migrate
- Flask-JWT-Extended
- Flask-CORS
- Gunicorn (production)

---

## Features

- JWT authentication with role-based access (learner / admin)
- Deck and flashcard CRUD with ownership enforcement
- Public community library with search and category filtering
- Study session management (start, pause, resume, complete)
- Spaced repetition scheduling based on card ratings
- Learning analytics (daily activity, streaks, top decks, completion rates)
- In-app notification system
- Content reporting and admin moderation
- User suspension and reactivation

---

## Project Structure

```
app/
├── models.py        # SQLAlchemy models
├── routes/          # Flask Blueprints (auth, decks, study, admin, etc.)
├── __init__.py      # App factory and config
config.py            # Environment-based configuration
run.py               # Entry point
seed.py              # Database seeding script
requirements.txt     # Python dependencies
```

---

## Getting Started

```bash
# Clone the repo
git clone https://github.com/jareelireri-ops/flashlearn_backend.git
cd flashlearn_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your DATABASE_URL, SECRET_KEY, JWT_SECRET_KEY

# Run migrations
flask db upgrade

# Seed the database
python seed.py

# Start the server
flask run
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Flask secret key |
| `JWT_SECRET_KEY` | JWT signing key |
| `CORS_ORIGINS` | Comma-separated list of allowed frontend origins |

---

## API Documentation

Full API reference is available in [API.md](./API.md).

---

## Related

- [Frontend Repository](https://github.com/jareelireri-ops/flashlearn_frontend)
