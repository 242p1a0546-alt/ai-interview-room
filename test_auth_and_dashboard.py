import io
import requests
import pymupdf


BASE_URL = "http://127.0.0.1:5000"

def create_sample_resume_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    resume_text = """SUDARSHAN REDDY
sudarshan@example.com | San Francisco, CA

EDUCATION
B.Tech in Computer Science & Engineering
Stanford University, Class of 2025 | 9.4 CGPA

TECHNICAL SKILLS
Languages: Python, SQL, JavaScript, C++
Frameworks: Flask, React, OpenCV, Scikit-Learn
Cloud: Docker, AWS, Git

PROJECTS
• AI Study Assistant (Python, Flask)
Engineered intelligent question generator and document analyzer with 92% semantic accuracy.

• Smart Attendance System (Python, OpenCV)
Implemented face recognition attendance pipeline reducing roll-call latency.
"""
    rect = pymupdf.Rect(50, 50, 545, 790)
    page.insert_textbox(rect, resume_text, fontsize=11, fontname="helv")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def run_tests():
    session = requests.Session()

    print("=== TEST 1: Public Landing Page ===")
    r = session.get(f"{BASE_URL}/")
    assert r.status_code == 200
    assert "AI Interview Room" in r.text
    assert "Your AI interviewer. Your next opportunity." in r.text
    assert "Login" in r.text
    assert "Create Account" in r.text
    print("[PASS] Landing page displays Login and Create Account buttons.")

    print("\n=== TEST 2: Protected Routes Reject Unauthenticated Users ===")
    r_dash = session.get(f"{BASE_URL}/dashboard", allow_redirects=False)
    assert r_dash.status_code in [302, 401]
    assert "/login" in r_dash.headers.get("Location", "")

    r_room = session.get(f"{BASE_URL}/interview", allow_redirects=False)
    assert r_room.status_code in [302, 401]
    assert "/login" in r_room.headers.get("Location", "")

    r_api = session.post(f"{BASE_URL}/api/resume/upload")
    assert r_api.status_code == 401
    print("[PASS] /dashboard, /interview, and /api/resume/upload correctly require login.")

    print("\n=== TEST 3: User Registration (/signup) Validation ===")
    # Password mismatch
    mismatch_data = {
        "full_name": "Sudarshan Reddy",
        "email": "sudarshan@example.com",
        "password": "Password123",
        "confirm_password": "WrongPassword123"
    }
    r = session.post(f"{BASE_URL}/signup", data=mismatch_data)
    assert "Passwords do not match" in r.text or r.status_code != 200

    # Password too short
    short_data = {
        "full_name": "Sudarshan Reddy",
        "email": "sudarshan@example.com",
        "password": "pass",
        "confirm_password": "pass"
    }
    r = session.post(f"{BASE_URL}/signup", data=short_data)
    assert "at least 8 characters" in r.text or r.status_code != 200

    import time
    test_email = f"test_user_{int(time.time())}@example.com"

    # Successful registration
    reg_data = {
        "full_name": "Sudarshan Reddy",
        "email": test_email,
        "password": "SecurePassword2026",
        "confirm_password": "SecurePassword2026"
    }
    r = session.post(f"{BASE_URL}/signup", data=reg_data, allow_redirects=True)
    assert r.status_code == 200
    assert "Welcome back, Sudarshan Reddy!" in r.text
    assert "Start New Interview" in r.text
    print("[PASS] User registration succeeds, session created, and redirected to /dashboard.")

    # Duplicate registration
    dup_session = requests.Session()
    r_dup = dup_session.post(f"{BASE_URL}/signup", data=reg_data)
    assert "already exists" in r_dup.text
    print("[PASS] Duplicate email registration is prevented.")

    print("\n=== TEST 4: User Logout (/logout) ===")
    r_logout = session.get(f"{BASE_URL}/logout", allow_redirects=True)
    assert r_logout.status_code == 200
    assert "Login" in r_logout.text

    # Verify dashboard is locked again
    r_check = session.get(f"{BASE_URL}/dashboard", allow_redirects=False)
    assert r_check.status_code == 302
    print("[PASS] Logout clears session; protected routes locked.")

    print("\n=== TEST 5: User Login (/login) ===")
    # Invalid password
    bad_login = {"email": test_email, "password": "WrongPassword"}
    r_bad = session.post(f"{BASE_URL}/login", data=bad_login)
    assert "Invalid email or password" in r_bad.text

    # Valid login
    good_login = {"email": test_email, "password": "SecurePassword2026", "remember_me": "on"}
    r_good = session.post(f"{BASE_URL}/login", data=good_login, allow_redirects=True)
    assert r_good.status_code == 200
    assert "Welcome back, Sudarshan Reddy!" in r_good.text
    print("[PASS] Login succeeds and redirects to personalized dashboard.")

    print("\n=== TEST 6: Authenticated Resume Upload & Interview Session ===")
    pdf_bytes = create_sample_resume_pdf()
    files = {"resume": ("sudarshan_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r_upload = session.post(f"{BASE_URL}/api/resume/upload", files=files)
    assert r_upload.status_code == 200, f"Upload error: {r_upload.text}"
    res_data = r_upload.json()["resume_data"]
    print(f"Candidate Detected: {res_data['candidate']['name']}")
    print(f"Skills: {res_data['skills'][:6]}")

    # Start Interview
    r_start = session.post(f"{BASE_URL}/api/interview/start", json={"resume_data": res_data})
    assert r_start.status_code == 200
    start_info = r_start.json()
    session_id = start_info["session_id"]
    print(f"Interview Started: session_id={session_id}")
    print(f"Q1: {start_info['question']}")

    # Submit Answer 1
    ans1 = "I am Sudarshan Reddy, a computer science student at Stanford. I built the Smart Attendance System using Python and OpenCV."
    r_ans1 = session.post(f"{BASE_URL}/api/interview/submit-answer", json={"session_id": session_id, "answer": ans1})
    assert r_ans1.status_code == 200
    res_ans1 = r_ans1.json()
    print(f"Q1 Score: {res_ans1['previous_evaluation']['score']}/100")
    print(f"Q2: {res_ans1['question']}")

    # End Interview & Save Record
    r_end = session.post(f"{BASE_URL}/api/interview/end", json={"session_id": session_id})
    assert r_end.status_code == 200
    report = r_end.json()
    print(f"Interview Concluded! Overall Score: {report['overall_score']}% ({report['recommendation']})")

    print("\n=== TEST 7: Dashboard Displays Previous Interview History ===")
    r_dash2 = session.get(f"{BASE_URL}/dashboard")
    assert r_dash2.status_code == 200
    assert "Previous Interviews" in r_dash2.text
    assert f"{report['overall_score']}%" in r_dash2.text
    assert "View Report" in r_dash2.text
    print("[PASS] Completed interview appears in user's dashboard history!")

    print("\n=== TEST 8: Fetching Stored Report via API ===")
    r_rep = session.get(f"{BASE_URL}/api/interview/report/{session_id}")
    assert r_rep.status_code == 200
    rep_data = r_rep.json()
    assert rep_data["overall_score"] == report["overall_score"]
    assert "project_understanding" in rep_data["metrics"]
    print("[PASS] Report retrieved successfully from SQLite database.")

    print("\n[ALL TESTS PASSED] Mandatory Authentication & Dashboard fully verified!")

if __name__ == "__main__":
    run_tests()
