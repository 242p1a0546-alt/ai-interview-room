import io
import requests
import pymupdf

BASE_URL = "http://127.0.0.1:5000"

def create_sample_resume_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842) # A4 size

    resume_text = """SUDARSHAN REDDY
sudarshan.reddy@example.com | +1 (555) 234-5678 | San Francisco, CA

EDUCATION
B.Tech in Computer Science & Engineering
Stanford University, Class of 2025 | 9.2 CGPA

TECHNICAL SKILLS
Languages: Python, Java, SQL, JavaScript, HTML, CSS, C++
Frameworks & Libraries: Flask, React, OpenCV, Scikit-Learn, Pandas, NumPy
Tools & Cloud: Docker, Git, AWS, Linux, REST API

PROJECTS
• AI Study Assistant (Python, Flask, Scikit-Learn)
Developed an intelligent academic study assistant using Python and Flask. Implemented document summarization and question generation using Scikit-Learn algorithms, achieving 92% classification accuracy. Built modular REST API endpoints for user querying.

• Smart Attendance System (Python, OpenCV)
Engineered an automated face recognition attendance tracker using Python and OpenCV. Processed real-time video feeds with Haar Cascades and localized face embeddings, reducing manual roll-call time by 80%.

CERTIFICATIONS
• Cisco Introduction to Data Science
• AWS Certified Cloud Practitioner

WORK EXPERIENCE
• Software Engineering Intern at TechCorp Solutions (Summer 2024)
Developed backend data ingestion pipelines in Python and SQL handling 50k daily events.
"""
    # Insert text into page
    rect = pymupdf.Rect(50, 50, 545, 790)
    page.insert_textbox(rect, resume_text, fontsize=11, fontname="helv")
    
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def run_resume_e2e_tests():
    session = requests.Session()
    # Ensure test user is registered / logged in for protected routes
    test_email = "test_resume_e2e@example.com"
    session.post(f"{BASE_URL}/signup", data={
        "full_name": "Sudarshan Reddy",
        "email": test_email,
        "password": "SecurePassword2026",
        "confirm_password": "SecurePassword2026"
    })
    session.post(f"{BASE_URL}/login", data={
        "email": test_email,
        "password": "SecurePassword2026"
    })

    print("=== 1. Generating Sample Resume PDF in Memory ===")
    pdf_bytes = create_sample_resume_pdf()
    print(f"Generated PDF: {len(pdf_bytes)} bytes")
    assert pdf_bytes.startswith(b"%PDF-")

    print("\n=== 2. Testing POST /api/resume/upload ===")
    files = {"resume": ("sudarshan_resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r = session.post(f"{BASE_URL}/api/resume/upload", files=files)
    assert r.status_code == 200, f"Upload failed: {r.text}"
    upload_res = r.json()
    assert upload_res["success"] is True
    res_data = upload_res["resume_data"]

    candidate = res_data["candidate"]
    print(f"Candidate Name: {candidate.get('name')}")
    print(f"College: {candidate.get('college')}")
    print(f"Branch: {candidate.get('branch')}")
    print(f"Skills Detected ({len(res_data['skills'])}): {res_data['skills']}")
    print(f"Projects Detected ({len(res_data['projects'])}): {[p['name'] for p in res_data['projects']]}")
    print(f"Certifications: {res_data['certifications']}")
    print(f"Experience: {res_data['experience']}")

    assert "Python" in res_data["skills"]
    assert "OpenCV" in res_data["skills"] or "SQL" in res_data["skills"]
    assert len(res_data["projects"]) >= 1

    print("\n=== 3. Testing POST /api/interview/start (Resume-Driven) ===")
    r = session.post(f"{BASE_URL}/api/interview/start", json={"resume_data": res_data})
    assert r.status_code == 200
    start_res = r.json()
    session_id = start_res["session_id"]
    print(f"Session Created: {session_id}")
    print(f"Question 1: {start_res['question']}")
    assert start_res["question_number"] == 1
    assert "Sudarshan" in start_res["question"] or "Sudarshan" in start_res["welcome_message"]

    print("\n=== 4. Testing Answer 1 (Candidate Introduces Background & Smart Attendance Project) ===")
    ans1 = (
        "I am Sudarshan Reddy, a final-year Computer Science student at Stanford. "
        "My core skills are Python, SQL, and Machine Learning. In my Smart Attendance System, "
        "I used Python and OpenCV to capture real-time camera frames and recognize student faces."
    )
    r = session.post(f"{BASE_URL}/api/interview/submit-answer", json={"session_id": session_id, "answer": ans1})
    assert r.status_code == 200
    res1 = r.json()
    print(f"Q1 Score: {res1['previous_evaluation']['score']}/100")
    print(f"Next Question (Q{res1['question_number']}): {res1['question']}")
    print(f"Category: {res1.get('category')}")
    print(f"Is Follow-up: {res1.get('is_followup')}")

    print("\n=== 5. Testing Answer 2 (Candidate Discusses OpenCV challenges) ===")
    ans2 = (
        "With OpenCV, we used Haar Cascade classifiers and face embeddings. The main challenge "
        "was lighting variation in the classroom and inference latency, which we optimized by downsampling frames."
    )
    r = session.post(f"{BASE_URL}/api/interview/submit-answer", json={"session_id": session_id, "answer": ans2})
    assert r.status_code == 200
    res2 = r.json()
    print(f"Q2 Score: {res2['previous_evaluation']['score']}/100")
    print(f"Next Question (Q{res2['question_number']}): {res2['question']}")

    print("\n=== 6. Simulating Remaining Questions Until Dynamic Conclusion ===")
    curr_res = res2
    q_count = 2
    while not curr_res.get("is_completed") and q_count < 6:
        q_count += 1
        ans = (
            "In our AI Study Assistant, we utilized Scikit-Learn for text classification and Flask "
            "for API endpoints. We evaluated models using precision and recall to avoid false predictions."
        )
        r = session.post(f"{BASE_URL}/api/interview/submit-answer", json={"session_id": session_id, "answer": ans})
        curr_res = r.json()
        print(f"Q{q_count} response -> is_completed: {curr_res.get('is_completed')}")

    print("\n=== 7. Testing GET /api/interview/report/<session_id> ===")
    r = session.get(f"{BASE_URL}/api/interview/report/{session_id}")
    assert r.status_code == 200
    report = r.json()
    print(f"Report Candidate: {report['candidate']['name']}")
    print(f"Overall Score: {report['overall_score']}/100")
    print(f"Recommendation: {report['recommendation']}")
    print(f"Metrics Breakdown: {report['metrics']}")
    print(f"Resume Strengths: {report['resume_strengths']}")
    print(f"Skills to Revise: {report.get('skills_to_revise')}")
    print(f"Project Topics to Prepare: {report.get('project_topics_to_prepare')}")
    print(f"Questions Evaluated: {report['total_questions']}")
    assert "project_understanding" in report["metrics"]
    assert "resume_knowledge" in report["metrics"]
    assert report["overall_score"] > 0

    print("\n[SUCCESS] All Resume-Driven AI Interview tests passed completely!")

if __name__ == "__main__":
    run_resume_e2e_tests()
