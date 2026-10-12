import requests

BASE_URL = "http://127.0.0.1:5000"

def test_full_flow():
    session = requests.Session()
    # Log in or sign up test account
    session.post(f"{BASE_URL}/signup", data={
        "full_name": "Alex Rivera",
        "email": "alex_e2e@example.com",
        "password": "Password12345",
        "confirm_password": "Password12345"
    })
    session.post(f"{BASE_URL}/login", data={
        "email": "alex_e2e@example.com",
        "password": "Password12345"
    })

    print("--- 1. Testing GET / (Landing Page & Frontend Assets) ---")
    r = session.get(BASE_URL)
    assert r.status_code == 200
    html = r.text
    assert "AI Interview Room" in html
    assert "Your AI interviewer. Your next opportunity." in html

    r_room = session.get(f"{BASE_URL}/interview")
    assert r_room.status_code == 200
    room_html = r_room.text
    assert "Upload Your Resume" in room_html or "AI Interview Room" in room_html
    assert "liveTranscriptBox" in room_html
    assert "startAnswerBtn" in room_html
    print("[PASS] GET / serves landing page and GET /interview serves interview room!")

    print("\n--- 2. Testing Static Assets ---")
    css_res = session.get(f"{BASE_URL}/static/css/style.css")
    assert css_res.status_code == 200
    assert len(css_res.text) > 1000
    js_app = session.get(f"{BASE_URL}/static/js/app.js")
    assert js_app.status_code == 200
    assert "InterviewSpeechModule" in js_app.text
    js_speech = session.get(f"{BASE_URL}/static/js/speech.js")
    assert js_speech.status_code == 200
    assert "webkitSpeechRecognition" in js_speech.text
    print("[PASS] Static CSS and JS modules served successfully!")

    print("\n--- 3. Testing POST /api/interview/start (Technical: Python, Medium) ---")
    start_payload = {
        "name": "Alex Rivera",
        "college": "Stanford University",
        "branch": "Computer Science",
        "year": "4th Year / Final Year",
        "interview_type": "Technical",
        "domain": "Python",
        "difficulty": "Medium"
    }
    r = session.post(f"{BASE_URL}/api/interview/start", json=start_payload)
    assert r.status_code == 200
    start_data = r.json()
    session_id = start_data["session_id"]
    print(f"Session Created: {session_id}")
    print(f"Initial Question: {start_data['question']}")
    assert start_data["question_number"] == 1
    assert "welcome_message" in start_data

    print("\n--- 4. Testing POST /api/interview/submit-answer (Answer 1) ---")
    ans1_payload = {
        "session_id": session_id,
        "answer": "Lists in Python are mutable sequences created with square brackets, while tuples are immutable sequences created with parentheses. Tuples are faster, take less memory, and can be used as dictionary keys."
    }
    r = session.post(f"{BASE_URL}/api/interview/submit-answer", json=ans1_payload)
    assert r.status_code == 200
    ans1_data = r.json()
    print(f"Q1 Score: {ans1_data['previous_evaluation']['score']}/100")
    print(f"Feedback: {ans1_data['previous_evaluation']['feedback']}")
    print(f"Is Follow-up: {ans1_data.get('is_followup')}")
    print(f"Next Question (Q{ans1_data['question_number']}): {ans1_data['question']}")

    print("\n--- 5. Testing POST /api/interview/submit-answer (Answer 2) ---")
    ans2_payload = {
        "session_id": session_id,
        "answer": "Immutability provides thread safety without mutex locks and ensures hash values remain consistent across the lifecycle."
    }
    r = session.post(f"{BASE_URL}/api/interview/submit-answer", json=ans2_payload)
    assert r.status_code == 200
    ans2_data = r.json()
    print(f"Q2 Score: {ans2_data['previous_evaluation']['score']}/100")
    print(f"Next Question (Q{ans2_data['question_number']}): {ans2_data['question']}")

    print("\n--- 6. Testing Dynamic Progression and End ---")
    curr_data = ans2_data
    q_iter = 2
    while not curr_data.get("is_completed") and q_iter < 6:
        q_iter += 1
        ans_payload = {
            "session_id": session_id,
            "answer": "Decorators wrap functions using higher-order functions. Memory management uses reference counting and generational garbage collection."
        }
        r = session.post(f"{BASE_URL}/api/interview/submit-answer", json=ans_payload)
        curr_data = r.json()
        print(f"Q{q_iter} answered -> is_completed: {curr_data.get('is_completed')}")

    print("\n--- 7. Testing GET /api/interview/report/<session_id> ---")
    r = session.get(f"{BASE_URL}/api/interview/report/{session_id}")
    assert r.status_code == 200
    report = r.json()
    print(f"Report Candidate: {report['candidate']['name']}")
    print(f"Report Overall Score: {report['overall_score']}/100")
    print(f"Recommendation: {report['recommendation']}")
    print(f"Metrics: {report['metrics']}")
    print(f"Strengths: {report['strengths']}")
    print(f"Questions Evaluated: {report['total_questions']}")
    assert report["overall_score"] > 0
    assert len(report["question_breakdown"]) > 0

    print("\n[SUCCESS] End-to-End HTTP test flow passed completely!")

if __name__ == "__main__":
    test_full_flow()
