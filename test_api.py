
import requests
import random

BASE_URL = "http://127.0.0.1:5000"

# email and password for testing, we generate a random email each time to avoid conflicts with existing users in the database, and ensure that the registration test can run multiple times without issues.
random_num = random.randint(1000, 9999)
test_email = f"tester_{random_num}@example.com"
test_password = "SecurePassword123!"

print("--- STARTING BACKEND FUNCTIONALITY TEST ---")

# 1. Test Registration
register_payload = {
    "name": "API Tester",
    "email": test_email,
    "password": test_password
}
reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json=register_payload)
print(f"1. Registration test: {reg_resp.status_code} - {reg_resp.json()}")

# 2. Test Login
login_payload = {
    "email": test_email,
    "password": test_password
}
login_resp = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
print(f"2. Login test: {login_resp.status_code}")
token = login_resp.json().get("access_token")

# set the token in the authorization header for subsequent requests to protected endpoints, 
headers = {"Authorization": f"Bearer {token}"}

# 3. Test Create Deck
deck_payload = {
    "title": "   Python Programming Basics   ", # Testing string trimming!
    "description": "Learn basic Python variables, loops and functions.",
    "category": "Computer Science",
    "difficulty_level": "easy",
    "is_public": True
}
deck_resp = requests.post(f"{BASE_URL}/api/decks", json=deck_payload, headers=headers)
print(f"3. Create Deck test: {deck_resp.status_code} - {deck_resp.json()}")
deck_id = deck_resp.json().get("deck", {}).get("id")

# 4. Test Add Flashcard
card_payload = {
    "question": "What is Python?",
    "answer": "A popular high-level programming language."
}
card_resp = requests.post(f"{BASE_URL}/api/decks/{deck_id}/flashcards", json=card_payload, headers=headers)
print(f"4. Add Flashcard test: {card_resp.status_code} - {card_resp.json()}")

# 5. Test Library Search
lib_resp = requests.get(f"{BASE_URL}/api/library?search=python", headers=headers)
print(f"5. Library Search test (looking for 'python'): {lib_resp.status_code}")
for deck in lib_resp.json():
    print(f"   Found Public Deck: {deck['title']} (Contains {deck['num_flashcards']} card(s))")

print("--- TEST RUN COMPLETED ---")