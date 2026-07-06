# FlashLearn — Backend

This is the backend API that runs the FlashLearn platform. It handles logging users in safely, tracking study history, calculating spaced repetition timelines, and sorting content reports for administrators.

* **Live API:** https://flashlearn-backend-ocnv.onrender.com
* **Frontend App:** https://flashlearn-frontend-ten.vercel.app

---

## Core Database Layout & Smart Design Choice

We designed this backend to be smart about how it handles data, making sure it handles real-world situations smoothly:

### 1. Sharing Decks Without Copying Data
* **No Wasted Space:** When a user saves a public deck from the library to their personal dashboard, the app doesn't make a duplicate copy of the deck. Instead, it uses a quick link table (`user_collection`) to connect the user to the original deck.
* **Instant Updates:** If the original creator edits a card or fixes a typo, every student tracking that deck instantly sees the update.

### 2. Guarding Student Progress
* **The Safety Net:** If a popular community creator decides to delete their account, a basic app would accidentally delete all their decks too. That would break the dashboards of hundreds of students who were studying them.
* **How We Fixed It:** Our system safely disconnects the creator's ID but keeps the deck alive in the database, meaning students never lose their study progress.

### 3. Separating Cards From Personal Scores
* **Individual Timers:** Flashcards only store the question and answer. All personal confidence scores and review schedules are saved in a completely separate table (`ReviewHistory`).
* **Multi-User Study:** This allows thousands of students to study the exact same public deck at the same time without their review histories getting mixed up.
  * Pressing **Easy** ➔ Shows the card again in 7 days.
  * Pressing **Medium** ➔ Shows the card again in 3 days.
  * Pressing **Hard** ➔ Shows the card again tomorrow.

### 4. Bouncers & Security Checks
* **Identity Protection:** Before letting someone edit or delete a card, the backend asks: *"Are you the person who created this?"* If not, it blocks them. This keeps public decks safe from being altered by random viewers.
* **Admin Controls:** Only users flagged as `admin` can look at content reports or suspend/reactivate troublesome accounts.

---

## Tech Stack
* **Language & Framework:** Python & Flask (organized into clean, feature-specific modules)
* **Database Management:** PostgreSQL with SQLAlchemy and Flask-Migrate for version tracking
* **Session Safety:** Flask-JWT-Extended (secure digital key passes for logged-in users)
* **Production Gateway:** Gunicorn & Web Hosting Configurations (`Procfile`)

---

## Project Structure
```text
flashlearn_backend/
├── app/
│   ├── routes/              # Split code folders managing features
│   │   ├── admin.py         # Moderation and user controls
│   │   ├── auth.py          # Signup, logins, and profile updates
│   │   ├── decks.py         # Deck creation, updates, and library searches
│   │   ├── notifications.py # Review reminders and alerts
│   │   └── study.py         # Card reviews and session bookmark tracking
│   ├── __init__.py          # Main app constructor and settings
│   └── models.py            # Database tables and field rules
├── migrations/              # Database version control folder
├── API.md                   # Full list of available endpoint URLs
├── config.py                # System settings loader
├── FLASHLEARN_ERD.png       # Visual blueprint of database tables
├── Procfile                 # Deployment instructions for production hosting
├── requirements.txt         # Required Python packages list
├── run.py                   # Main backend starter file
├── seed.py                  # Script to fill local database with test data
├── test_api.py              # Automated test cases
└── update_admin.py          # Quick tool to update admin details
```

---

## Getting Started

### Local Setup Steps

**1. Clone the repository**
```bash
git clone https://github.com/jareelireri-ops/flashlearn_backend.git
cd flashlearn_backend
```

**2. Create and turn on a virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows users: venv\Scripts\activate
```

**3. Install the package dependencies**
```bash
pip install -r requirements.txt
```

**4. Set up your environment settings**

Create your own local configuration file:
```bash
cp .env.example .env
```
Open the new `.env` file and fill in your local keys (`DATABASE_URL`, `SECRET_KEY`, and `JWT_SECRET_KEY`).

**5. Build your database tables and insert sample data**
```bash
flask db upgrade
python seed.py
```

**6. Fire up the local backend server**
```bash
flask run
```

---

## Environment Variables Configuration

| Variable | What It Does |
|---|---|
| `DATABASE_URL` | The direct connection pathway to your PostgreSQL database |
| `SECRET_KEY` | Secure security salt for processing requests |
| `JWT_SECRET_KEY` | The secret validation key for verifying logged-in user tokens |
| `CORS_ORIGINS` | Tells the backend which frontend website URL is allowed to talk to it |

---

## Related Repositories
* [Frontend Client Repository](https://flashlearn-frontend-ten.vercel.app)