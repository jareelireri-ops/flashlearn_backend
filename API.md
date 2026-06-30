# FlashLearn API Documentation

Base URL (local): `http://127.0.0.1:5000/api`
Health check: `GET http://127.0.0.1:5000/`

## Authentication

All protected routes require a JWT in the header:

```
Authorization: Bearer <access_token>
```

Tokens are returned on login and expire after 2 hours.

---

## Auth — `/api/auth`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/register` | No | Create account |
| POST | `/login` | No | Sign in, returns JWT |
| GET | `/profile` | Yes | Get current user profile |
| PUT | `/profile` | Yes | Update name / profile picture URL |
| POST | `/forgot-password` | No | Request password reset token |
| POST | `/reset-password` | No | Reset password with token |

### POST `/auth/register`

```json
{ "name": "Jane Doe", "email": "jane@example.com", "password": "secret123" }
```

Response 201:

```json
{ "message": "...", "user_id": 1 }
```

### POST `/auth/login`

```json
{ "email": "jane@example.com", "password": "secret123" }
```

Response 200:

```json
{
  "message": "Login successful",
  "access_token": "<jwt>",
  "user": { "id": 1, "name": "Jane Doe", "email": "jane@example.com", "role": "learner" }
}
```

### POST `/auth/forgot-password`

```json
{ "email": "jane@example.com" }
```

Response 200:

```json
{ "message": "If that email exists, a reset link has been sent", "reset_token": "<token>" }
```

Note: `reset_token` is returned for development only. In production, send via email.

### POST `/auth/reset-password`

```json
{ "token": "<reset_token>", "new_password": "newsecret123" }
```

---

## Decks — `/api`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/decks` | Yes | Create deck |
| GET | `/decks` | Yes | List user's own decks |
| GET | `/decks/:id` | Yes | Deck details |
| PUT | `/decks/:id` | Yes | Update deck (owner only) |
| DELETE | `/decks/:id` | Yes | Delete deck (owner only) |
| GET | `/decks/:id/preview` | No | First card question teaser |
| GET | `/decks/:id/flashcards` | Yes | List flashcards |
| POST | `/decks/:id/flashcards` | Yes | Add flashcard (owner only) |
| PUT | `/flashcards/:id` | Yes | Update flashcard (owner only) |
| DELETE | `/flashcards/:id` | Yes | Delete flashcard (owner only) |

### POST `/decks`

```json
{
  "title": "Python Basics",
  "description": "Core Python concepts",
  "category": "Programming",
  "tags": "python, beginner",
  "is_public": true,
  "difficulty_level": "medium"
}
```

### POST `/decks/:id/flashcards`

```json
{
  "question": "What is a list?",
  "answer": "An ordered mutable collection",
  "difficulty_level": "easy",
  "image_url": null
}
```

---

## Library & Collection — `/api`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/public/categories` | No | Categories with deck counts |
| GET | `/public/decks` | No | Browse public decks |
| GET | `/library` | Yes | Authenticated library browse |
| GET | `/collection` | Yes | User's learning collection |
| POST | `/collection/add/:deck_id` | Yes | Save public deck to collection |
| DELETE | `/collection/remove/:deck_id` | Yes | Remove saved deck |

Query params for `/public/decks` and `/library`: `?search=`, `?category=`, `?difficulty=easy|medium|hard`

---

## Study Sessions — `/api`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/study/:deck_id/start` | Yes | Start study session |
| GET | `/study/:deck_id/active` | Yes | Get active/paused session |
| GET | `/study/sessions/:id/card` | Yes | Get current card |
| POST | `/study/sessions/:id/review` | Yes | Rate a card |
| PATCH | `/study/sessions/:id/pause` | Yes | Pause session |
| PATCH | `/study/sessions/:id/resume` | Yes | Resume session |
| PATCH | `/study/sessions/:id/complete` | Yes | Complete session |
| GET | `/study/review-queue` | Yes | Cards due for review |
| GET | `/study/dashboard` | Yes | Dashboard stats |

### POST `/study/sessions/:id/review`

```json
{ "flashcard_id": 5, "rating": "easy" }
```

Ratings: `easy` (review in 7 days), `medium` (3 days), `hard` (1 day)

### GET `/study/dashboard` response

```json
{
  "total_sessions": 12,
  "total_cards_reviewed": 84,
  "study_streak": 5,
  "cards_due_today": 3
}
```

---

## Analytics — `/api/study/analytics`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/daily?days=7` | Cards reviewed per day |
| GET | `/weekly` | Weekly activity |
| GET | `/monthly` | Monthly activity |
| GET | `/top-decks` | Top 5 most studied decks (by review count) |
| GET | `/difficult-cards` | Cards rated "hard" most often |
| GET | `/completion` | Deck completion percentages |

---

## Notifications — `/api/notifications`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/notifications` | Yes | List notifications (`?unread=true`) |
| GET | `/notifications/unread-count` | Yes | Unread badge count |
| PUT | `/notifications/:id/read` | Yes | Mark one as read |
| PUT | `/notifications/read-all` | Yes | Mark all as read |
| DELETE | `/notifications/:id` | Yes | Delete notification |
| POST | `/notifications/check-due` | Yes | Create review-due notification if cards are due |

Notification types: `review_due`, `collection_added`, `deck_updated`

---

## Reports — `/api`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/reports` | Yes | Submit content report |

```json
{ "deck_id": 3, "reason": "Inappropriate content" }
```

---

## Admin — `/api/admin` (admin role only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/users` | List all users |
| PUT | `/users/:id/status` | Suspend/reactivate user |
| GET | `/reports` | View reports (`?status=pending`) |
| PUT | `/reports/:id` | Resolve report |
| DELETE | `/content` | Delete deck or flashcard |

### PUT `/admin/users/:id/status`

```json
{ "is_active": false }
```

---

## Error Responses

All errors return JSON:

```json
{ "error": "Human-readable message" }
```

| Code | Meaning |
|------|---------|
| 400 | Bad request / validation failed |
| 401 | Missing or invalid JWT |
| 403 | Forbidden (suspended account, wrong role, no permission) |
| 404 | Resource not found |
| 500 | Server error |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Flask secret key |
| `JWT_SECRET_KEY` | JWT signing key |
