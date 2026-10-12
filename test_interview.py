import sys
import os

from interview_engine import (
    start_resume_interview,
    process_resume_answer,
    generate_resume_report,
    SESSIONS
)

def run_tests():
    print("=== TEST 1: Starting Session ===")
    resume_data = {
        "candidate": {
            "name": "Alex Rivera",
            "college": "MIT",
            "branch": "Computer Science",
            "year": "4th Year"
        },
        "education": "B.Tech in Computer Science, MIT (2025)",
        "skills": ["Python", "SQL", "Machine Learning", "Data Structures"],
        "projects": [
            {
                "name": "ML Pipeline Optimizer",
                "description": "Built an automated ML model evaluation pipeline.",
                "technologies": ["Python", "Scikit-Learn", "Flask"],
                "claims": ["Achieved 94% classification accuracy on imbalanced datasets."]
            }
        ],
        "certifications": ["AWS Certified Cloud Practitioner"],
        "experience": "Software Engineering Intern at DataCorp (Summer 2024)"
    }
    session_data = start_resume_interview(resume_data)
    session_id = session_data["session_id"]
    print(f"Session started: ID={session_id}")
    print(f"Question 1: {session_data['question']}")
    assert session_data["question_number"] == 1
    assert "session_id" in session_data

    print("\n=== TEST 2: Submitting Answer 1 (Strong Answer on Memory/Decorators/GIL) ===")
    strong_answer = (
        "In Python, memory management relies on reference counting where an object is deallocated "
        "when references reach zero. To handle cyclic references, Python's generational garbage collection "
        "runs across three generations. Also, decorators are higher order functions that wrap another function, "
        "often using functools.wraps to preserve function metadata."
    )
    res1 = process_resume_answer(session_id, strong_answer)
    print(f"Eval 1 Score: {res1['previous_evaluation']['score']}/100")
    print(f"Feedback: {res1['previous_evaluation']['feedback']}")
    print(f"Difficulty changed: {res1.get('difficulty_changed')} to {res1.get('difficulty')}")
    print(f"Next Question (Q{res1['question_number']}): {res1['question']}")
    assert res1["previous_evaluation"]["score"] >= 50

    print("\n=== TEST 3: Follow-up or Adaptive Question 2 ===")
    fu_answer = "Immutability is essential because it guarantees thread safety and allows objects to be hashable as dictionary keys."
    res2 = process_resume_answer(session_id, fu_answer)
    print(f"Eval 2 Score: {res2['previous_evaluation']['score']}/100")
    print(f"Next Question (Q{res2['question_number']}): {res2['question']}")

    print("\n=== TEST 4: Simulating answers until dynamic completion ===")
    q_count = 2
    while not res2.get("is_completed") and q_count < 7:
        q_count += 1
        ans = "Lists are mutable whereas tuples are immutable and consume less memory. In multithreading, GIL prevents simultaneous bytecode execution."
        res2 = process_resume_answer(session_id, ans)
        print(f"Q{q_count} response -> is_completed: {res2.get('is_completed')}")
        if res2.get("is_completed"):
            print(f"Interview ended dynamically! Reason: {res2.get('completion_reason')}")
            break

    print("\n=== TEST 5: Generating Final Performance Report ===")
    report = generate_resume_report(session_id)
    print(f"Candidate: {report['candidate']['name']}")
    print(f"Overall Score: {report['overall_score']}/100")
    print(f"Recommendation: {report['recommendation']}")
    print(f"Metrics: {report['metrics']}")
    print(f"Strengths: {report['strengths']}")
    print(f"Total Questions Evaluated: {report['total_questions']}")
    assert report["overall_score"] > 0
    assert len(report["question_breakdown"]) > 0

    print("\n[SUCCESS] All automated backend test cases passed successfully!")

if __name__ == "__main__":
    run_tests()
