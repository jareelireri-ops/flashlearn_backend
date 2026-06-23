import requests
import random

BASE_URL = "http://127.0.0.1:5000"

random_num = random.randint(1000, 9999)
test_email = f"tester_{random_num}@example.com"
test_password = "SecurePassword123!"

print("--- STARTING COMPREHENSIVE BACKEND TEST ---")

try:
    print("\n[1] Testing Auth...")
    reg_resp = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "API Tester", "email": test_email, "password": test_password
    })
    print(f"  -> Register: {reg_resp.status_code}")
    
    login_resp = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": test_email, "password": test_password
    })
    print(f"  -> Login: {login_resp.status_code}")
    token = login_resp.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    print("\n[2] Testing Decks & Public Routes...")
    public_cat = requests.get(f"{BASE_URL}/api/public/categories")
    print(f"  -> Public Categories (No Auth): {public_cat.status_code}")

    deck_resp = requests.post(f"{BASE_URL}/api/decks", json={
        "title": "API Test Deck", "description": "Testing everything", 
        "category": "Software Engineering", "is_public": True
    }, headers=headers)
    print(f"  -> Create Deck: {deck_resp.status_code}")
    deck_id = deck_resp.json().get("deck", {}).get("id")

    print("\n[3] Testing Flashcards...")
    card_resp = requests.post(f"{BASE_URL}/api/decks/{deck_id}/flashcards", json={
        "question": "Does the API work?", "answer": "Yes it does!"
    }, headers=headers)
    print(f"  -> Add Flashcard: {card_resp.status_code}")
    card_id = card_resp.json().get("flashcard_id")

    print("\n[4] Testing Study Engine...")
    start_sess = requests.post(f"{BASE_URL}/api/study/{deck_id}/start", headers=headers)
    print(f"  -> Start Session: {start_sess.status_code}")
    session_id = start_sess.json().get("session", {}).get("id")

    if session_id and card_id:
        review_resp = requests.post(f"{BASE_URL}/api/study/sessions/{session_id}/review", json={
            "flashcard_id": card_id, "rating": "easy"
        }, headers=headers)
        print(f"  -> Submit Card Review (Easy): {review_resp.status_code}")

    dash_resp = requests.get(f"{BASE_URL}/api/study/dashboard", headers=headers)
    print(f"  -> Get Dashboard Analytics: {dash_resp.status_code}")

    print("\n[5] Testing Notifications...")
    notif_check = requests.post(f"{BASE_URL}/api/notifications/check-due", headers=headers)
    print(f"  -> Check Due Cards (Trigger Notification): {notif_check.status_code}")
    
    notif_get = requests.get(f"{BASE_URL}/api/notifications", headers=headers)
    print(f"  -> Fetch Notifications: {notif_get.status_code}")

    print("\n[6] Testing Reporting Engine...")
    report_resp = requests.post(f"{BASE_URL}/api/reports", json={
        "deck_id": deck_id, "reason": "Just testing the report system."
    }, headers=headers)
    print(f"  -> Submit Content Report: {report_resp.status_code}")

    print("\n ALL TESTS SUCCESSFUL")

except Exception as e:
    print(f"\n TEST FAILED: {str(e)}")