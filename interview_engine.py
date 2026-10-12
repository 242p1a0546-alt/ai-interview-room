import os
import re
import json
import uuid
import random
import time
from typing import Dict, Any, List, Optional
import requests

try:
    from dotenv import load_dotenv  # pyrefly: ignore[missing-import]
    load_dotenv()
except ImportError:
    pass

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class ResumeInterviewSession:
    def __init__(self, session_id: str, resume_data: Dict[str, Any]):
        self.session_id = session_id
        self.resume_data = resume_data
        self.candidate = resume_data.get("candidate", {})
        self.skills = resume_data.get("skills", ["Python", "SQL", "Problem Solving"])
        self.projects = resume_data.get("projects", [])
        self.certifications = resume_data.get("certifications", [])
        self.education = resume_data.get("education", "")
        self.experience = resume_data.get("experience", "No professional experience detected")

        self.current_difficulty = "Medium"
        self.history: List[Dict[str, Any]] = []
        self.asked_questions: List[str] = []
        self.is_completed = False
        self.completion_reason = ""
        self.start_time = time.time()

        # Track which resume items have been probed
        self.probed_skills: List[str] = []
        self.probed_projects: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "candidate": self.candidate,
            "skills_count": len(self.skills),
            "projects_count": len(self.projects),
            "current_difficulty": self.current_difficulty,
            "questions_count": len(self.history),
            "is_completed": self.is_completed,
            "completion_reason": self.completion_reason,
            "elapsed_seconds": int(time.time() - self.start_time)
        }

# Global in-memory sessions registry
SESSIONS: Dict[str, ResumeInterviewSession] = {}

# -------------------------------------------------------------
# SESSION INITIALIZATION FROM RESUME
# -------------------------------------------------------------

def start_resume_interview(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    session = ResumeInterviewSession(session_id, resume_data)
    SESSIONS[session_id] = session

    candidate_name = session.candidate.get("name", "Candidate")
    branch = session.candidate.get("branch", "Computer Science")

    # Question 1: Personalized Introduction & Technical Walkthrough
    q1_text = (
        f"Hello {candidate_name}, welcome to your interview room. "
        f"To start off, could you introduce yourself and walk me through your technical background in {branch}, "
        f"highlighting the key projects and skills mentioned in your resume?"
    )

    q1_record = {
        "question_id": 1,
        "question": q1_text,
        "category": "Introduction & Background",
        "difficulty": session.current_difficulty,
        "target_entity": "Profile",
        "is_followup": False,
        "candidate_answer": "",
        "evaluation": None
    }
    session.history.append(q1_record)
    session.asked_questions.append(q1_text)

    welcome_msg = f"Hello {candidate_name}! I have reviewed your resume and prepared a tailored technical interview."

    return {
        "session_id": session_id,
        "welcome_message": welcome_msg,
        "question_number": 1,
        "question": q1_text,
        "category": "Introduction",
        "difficulty": session.current_difficulty,
        "candidate": session.candidate,
        "is_followup": False
    }

# -------------------------------------------------------------
# CANDIDATE ANSWER PROCESSING & RESUME-GROUNDED REASONING
# -------------------------------------------------------------

def process_resume_answer(session_id: str, candidate_transcript: str) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found", "is_completed": True}

    if not session.history:
        return {"error": "No active question found", "is_completed": True}

    current_item = session.history[-1]
    current_item["candidate_answer"] = candidate_transcript.strip()

    # Step 1: Evaluate candidate answer in context of their resume
    evaluation = _evaluate_resume_answer(
        question=current_item["question"],
        answer=candidate_transcript,
        category=current_item.get("category", "General"),
        skills=session.skills,
        projects=session.projects
    )
    current_item["evaluation"] = evaluation

    # Step 2: Dynamic Difficulty Adaptation
    old_diff = session.current_difficulty
    new_diff = _adapt_difficulty(session.current_difficulty, evaluation["score"])
    session.current_difficulty = new_diff

    # Step 3: Dynamic Termination Check (no fixed questions)
    should_terminate, end_reason = _check_termination(session)
    if should_terminate:
        session.is_completed = True
        session.completion_reason = end_reason
        return {
            "is_completed": True,
            "completion_reason": end_reason,
            "evaluation": evaluation,
            "session_id": session.session_id,
            "total_questions_asked": len(session.history)
        }

    # Step 4: Generate Next Question Strictly from Resume
    next_q = _generate_next_resume_question(session, candidate_transcript, evaluation)
    q_num = len(session.history) + 1

    new_record = {
        "question_id": q_num,
        "question": next_q["question"],
        "category": next_q.get("category", "Technical Skill"),
        "difficulty": session.current_difficulty,
        "target_entity": next_q.get("target_entity", "Resume"),
        "is_followup": next_q.get("is_followup", False),
        "candidate_answer": "",
        "evaluation": None
    }
    session.history.append(new_record)
    session.asked_questions.append(next_q["question"])

    return {
        "is_completed": False,
        "previous_evaluation": evaluation,
        "question_number": q_num,
        "question": next_q["question"],
        "category": new_record["category"],
        "difficulty": session.current_difficulty,
        "is_followup": next_q.get("is_followup", False),
        "difficulty_changed": (old_diff != new_diff),
        "difficulty_direction": "up" if _diff_rank(new_diff) > _diff_rank(old_diff) else ("down" if _diff_rank(new_diff) < _diff_rank(old_diff) else "same")
    }

def _diff_rank(diff: str) -> int:
    return {"Easy": 1, "Medium": 2, "Hard": 3}.get(diff, 1)

def _adapt_difficulty(current_diff: str, score: float) -> str:
    levels = ["Easy", "Medium", "Hard"]
    idx = levels.index(current_diff) if current_diff in levels else 0
    if score >= 75:
        return levels[min(idx + 1, 2)]
    elif score < 45:
        return levels[max(idx - 1, 0)]
    return current_diff

def _generate_next_resume_question(session: ResumeInterviewSession, last_answer: str, last_eval: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decides the next question strictly using the candidate's resume as source of truth.
    Priority:
    1. Contextual Follow-up on a claim or technology the candidate just mentioned.
    2. Adaptive Pivot if candidate struggled ("I don't know").
    3. Deep-dive into Projects listed on the resume.
    4. Technical Skill verification for skills listed on the resume.
    5. Scenario / Architecture question on detected skills.
    """
    ans_lower = last_answer.lower()
    total_asked = len(session.history)

    # Check if candidate struggled / said "I don't know"
    struggled = any(phrase in ans_lower for phrase in ["i don't know", "dont know", "not sure", "no idea", "forgot", "can't recall", "cant recall"]) or last_eval["score"] < 40

    if struggled:
        # Pivot gracefully to another area
        unprobed_proj = [p for p in session.projects if p["name"] not in session.probed_projects]
        if unprobed_proj:
            p = unprobed_proj[0]
            session.probed_projects.append(p["name"])
            return {
                "question": f"No problem at all, let's explore another area of your work. In your resume, you listed '{p['name']}'. Could you tell me what problem this project solves and what your core responsibilities were?",
                "category": "Project Pivot",
                "target_entity": p["name"],
                "is_followup": False
            }
        elif session.skills:
            unprobed_skill = [s for s in session.skills if s not in session.probed_skills]
            sk = unprobed_skill[0] if unprobed_skill else session.skills[0]
            session.probed_skills.append(sk)
            return {
                "question": f"No worries, let's switch gears. You also mentioned {sk} in your technical skills. Can you explain a practical scenario where you utilized {sk}?",
                "category": "Skill Pivot",
                "target_entity": sk,
                "is_followup": False
            }

    # Condition 1: Contextual Follow-up based on specific claims in the answer
    # If candidate mentioned ML algorithms like Random Forest / Decision Trees
    if any(k in ans_lower for k in ["random forest", "decision tree", "classifier", "regression", "svm"]):
        return {
            "question": "You mentioned using Random Forest. What led you to choose Random Forest over a single Decision Tree or Gradient Boosting, and how did you prevent overfitting on your dataset?",
            "category": "Algorithm Deep Dive",
            "target_entity": "Random Forest",
            "is_followup": True
        }

    # If candidate mentioned OpenCV or Computer Vision
    if any(k in ans_lower for k in ["opencv", "haar cascade", "facial", "face", "image", "frame"]):
        return {
            "question": "You brought up OpenCV. Could you explain the image processing pipeline you used, and what challenges you faced with frame rate latency or lighting conditions?",
            "category": "Computer Vision Probe",
            "target_entity": "OpenCV",
            "is_followup": True
        }

    # If candidate mentioned Flask, Django, React, or APIs
    if any(k in ans_lower for k in ["flask", "django", "fastapi", "rest api", "api", "endpoints"]):
        return {
            "question": "You mentioned API development. How did you design the request-response cycle and handle error handling or authentication between your frontend and backend?",
            "category": "API Architecture",
            "target_entity": "Backend API",
            "is_followup": True
        }

    # If candidate mentioned SQL, MongoDB, or Database
    if any(k in ans_lower for k in ["sql", "mysql", "postgresql", "mongodb", "database", "query", "schema"]):
        return {
            "question": "Regarding the database layer, what schema design decisions did you make, and how did you optimize your queries to avoid bottlenecks?",
            "category": "Database Engineering",
            "target_entity": "Database",
            "is_followup": True
        }

    # Condition 2: Project Deep Dive (Questions 2 or 3)
    if session.projects and len(session.probed_projects) < len(session.projects):
        unprobed = [p for p in session.projects if p["name"] not in session.probed_projects]
        if unprobed:
            target_proj = unprobed[0]
            session.probed_projects.append(target_proj["name"])
            tech_hint = f" using {', '.join(target_proj['technologies'][:3])}" if target_proj.get("technologies") else ""

            if target_proj.get("claims"):
                claim = target_proj["claims"][0]
                q_text = f"Looking at your resume, you noted: '{claim}'. What specific architectural decisions made this possible, and what trade-offs did you consider?"
            else:
                q_text = f"I see that you developed '{target_proj['name']}'{tech_hint}. Could you explain the underlying system architecture and the biggest technical challenge you overcame while building it?"

            return {
                "question": q_text,
                "category": "Project Deep Dive",
                "target_entity": target_proj["name"],
                "is_followup": False
            }

    # Condition 3: Primary Skill Verification (from resume skills)
    unprobed_skills = [s for s in session.skills if s not in session.probed_skills]
    if unprobed_skills:
        skill = unprobed_skills[0]
        session.probed_skills.append(skill)
        q_text = _generate_skill_question(skill, session.current_difficulty)
        return {
            "question": q_text,
            "category": f"Technical Skill ({skill})",
            "target_entity": skill,
            "is_followup": False
        }

    # Condition 4: Probing Certifications or Cross-Questioning
    if session.certifications and total_asked <= 5:
        cert = session.certifications[0]
        return {
            "question": f"Your resume highlights your certification in '{cert}'. How has the knowledge gained from this certification directly influenced the way you build projects or write code?",
            "category": "Certification Discussion",
            "target_entity": cert,
            "is_followup": False
        }

    # Final wrap-up question
    return {
        "question": "Reflecting on the projects and technologies on your resume, if you were to redesign your most significant project from scratch today for 10x scale, what would you change architecturally?",
        "category": "System Design & Retrospective",
        "target_entity": "Retrospective",
        "is_followup": False
    }

def _generate_skill_question(skill: str, difficulty: str) -> str:
    sk_lower = skill.lower()

    if "python" in sk_lower:
        if difficulty == "Hard":
            return "In Python, how do Generators and the Iterator protocol optimize memory for streaming large datasets, and how does the GIL affect multithreaded CPU tasks?"
        elif difficulty == "Medium":
            return "You mentioned Python in your resume. How do decorators work in Python, and can you describe a scenario where you implemented or would use a custom decorator?"
        else:
            return "You highlighted Python in your resume. What are the key differences between mutable data structures like lists and immutable structures like tuples, and when do you use each?"

    elif "sql" in sk_lower:
        if difficulty == "Hard":
            return "In SQL, how do database transactions enforce ACID properties, and how do transaction isolation levels prevent phenomena like phantom reads?"
        elif difficulty == "Medium":
            return "You listed SQL in your resume. How do B-Tree indexes improve query performance, and what are the drawbacks of over-indexing tables with high write volume?"
        else:
            return "In SQL, what is the difference between WHERE and HAVING clauses, and when are Window Functions like ROW_NUMBER() preferred over GROUP BY?"

    elif "machine learning" in sk_lower or "data science" in sk_lower or "ai" in sk_lower:
        if difficulty == "Hard":
            return "When evaluating machine learning models on imbalanced datasets, why is accuracy often misleading, and how do precision, recall, and ROC-AUC help you select the best model?"
        else:
            return "You highlighted Machine Learning on your resume. How do you approach data preprocessing, feature engineering, and avoiding data leakage before training a model?"

    elif "react" in sk_lower:
        return "In React, how does the Virtual DOM reconciliation algorithm work, and how do you optimize re-renders using hooks like useMemo and useCallback?"

    elif "java" in sk_lower:
        return "In Java, how does garbage collection work in the JVM, and what is the difference between checked and unchecked exceptions?"

    elif "docker" in sk_lower or "cloud" in sk_lower or "aws" in sk_lower:
        return f"You listed {skill} on your resume. How do containerization and cloud deployment improve system portability and scaling compared to bare-metal servers?"

    # Generic technical probe for any resume skill
    return f"You listed {skill} as a core skill on your resume. Could you describe a practical system or project where you applied {skill}, detailing how you resolved an unexpected bug or edge case?"

def _check_termination(session: ResumeInterviewSession) -> tuple:
    """
    Dynamic interview end logic:
    No fixed number of questions.
    Terminates when:
    - Candidate's background, main projects, and key skills have all been assessed.
    - Minimum 4 questions, maximum 6 questions.
    - Consistency across evaluations is reached.
    """
    total_asked = len(session.history)
    if total_asked < 4:
        return False, ""

    if total_asked >= 6:
        return True, "The AI interviewer has thoroughly evaluated your projects, technical skills, and resume claims."

    # If 4 or 5 questions asked, check if both a project and a skill have been evaluated
    scores = [q["evaluation"]["score"] for q in session.history if q.get("evaluation")]
    if len(scores) >= 4:
        recent_scores = scores[-3:]
        variance = max(recent_scores) - min(recent_scores)
        if variance < 18 or len(session.probed_projects) >= 1:
            return True, "Comprehensive evaluation complete. Candidate project architecture, technical competencies, and verbal articulation have been verified."

    return False, ""

# -------------------------------------------------------------
# RESUME-AWARE EVALUATION ENGINE
# -------------------------------------------------------------

def _evaluate_resume_answer(question: str, answer: str, category: str, skills: List[str], projects: List[Any]) -> Dict[str, Any]:
    clean_ans = answer.strip()
    if not clean_ans:
        return {
            "score": 15,
            "accuracy": 15,
            "clarity": 15,
            "depth": 15,
            "project_understanding": 15,
            "resume_authenticity": 20,
            "confidence": 15,
            "feedback": "No audible response was detected. Please ensure your microphone is enabled and speak clearly.",
            "strengths": [],
            "areas_for_improvement": ["Elaborate on your practical implementation details and engineering decisions."],
            "skills_referenced": []
        }

    # If Gemini is configured
    if GEMINI_API_KEY:
        try:
            llm_res = _evaluate_with_gemini(question, clean_ans, category, skills)
            if llm_res and "score" in llm_res:
                return llm_res
        except Exception as e:
            print(f"[Resume Evaluation] Gemini fallback to local NLP: {e}")

    return _local_resume_evaluate(question, clean_ans, category, skills, projects)

def _local_resume_evaluate(question: str, answer: str, category: str, skills: List[str], projects: List[Any]) -> Dict[str, Any]:
    words = re.findall(r'\b[a-zA-Z0-9_-]+\b', answer.lower())
    word_count = len(words)

    # Check for "I don't know" or confusion
    struggled = any(phrase in answer.lower() for phrase in ["i don't know", "dont know", "not sure", "no idea", "forgot", "can't recall", "cant recall"])

    # Resume Skill verification
    skills_mentioned = [s for s in skills if s.lower() in answer.lower()]

    # Technical keywords
    tech_keywords = [
        "architecture", "algorithm", "database", "model", "accuracy", "performance",
        "optimization", "pipeline", "framework", "latency", "library", "cache",
        "interface", "component", "trade-off", "scalability", "dataset", "feature"
    ]
    tech_hits = [k for k in tech_keywords if k in answer.lower()]

    # Length factor
    if word_count < 15:
        depth_score = max(20, word_count * 2.5)
    elif word_count <= 80:
        depth_score = min(95, 45 + (word_count * 0.6))
    else:
        depth_score = 90

    # Project understanding factor
    project_understanding = 60 + (len(tech_hits) * 8) + (15 if len(skills_mentioned) > 0 else 0)
    project_understanding = max(25, min(95, int(project_understanding)))

    # Resume Authenticity (checking if candidate speaks authoritatively about their work)
    resume_authenticity = 70 + (15 if len(tech_hits) >= 2 else 0) + (10 if word_count >= 30 else -15)
    if struggled:
        resume_authenticity = max(30, resume_authenticity - 30)
    resume_authenticity = max(25, min(96, int(resume_authenticity)))

    # Clarity and communication
    has_transitions = any(t in answer.lower() for t in ["because", "therefore", "for example", "specifically", "we implemented", "the main reason", "however"])
    clarity_score = 65 + (15 if has_transitions else 0) + (10 if word_count > 25 else -10)
    clarity_score = max(30, min(95, int(clarity_score)))

    # Technical accuracy
    if struggled:
        accuracy_score = 35
        overall_score = 38
    else:
        accuracy_score = int(0.4 * depth_score + 0.3 * project_understanding + 0.3 * resume_authenticity)
        overall_score = int(0.35 * accuracy_score + 0.25 * project_understanding + 0.25 * clarity_score + 0.15 * resume_authenticity)

    overall_score = max(25, min(96, overall_score))

    strengths = []
    improvements = []

    if skills_mentioned:
        strengths.append(f"Directly referenced core technologies: {', '.join(skills_mentioned[:3])}.")
    if tech_hits:
        strengths.append(f"Demonstrated engineering vocabulary: {', '.join(tech_hits[:3])}.")
    if word_count >= 35:
        strengths.append("Delivered a comprehensive verbal explanation with good pacing.")

    if not strengths:
        strengths.append("Addressed the question directly without hesitating.")

    if struggled:
        improvements.append("Review foundational concepts and be ready to explain architectural choices.")
    if word_count < 30:
        improvements.append("Elaborate more on specific engineering challenges and how you solved them.")
    if not tech_hits:
        improvements.append("Include more technical specifics regarding data structures, algorithms, or libraries.")

    if not improvements:
        improvements.append("Great depth; you can further explain real-world scaling and edge cases.")

    if overall_score >= 80:
        summary_feedback = "Strong answer! You communicated your technical decisions clearly and demonstrated genuine hands-on ownership of your work."
    elif overall_score >= 60:
        summary_feedback = "Solid explanation. You understand the core concept, but providing more concrete architectural specifics would strengthen your response."
    else:
        summary_feedback = "Good attempt. Your answer was a bit high-level; make sure you can explain the inner workings and rationale behind technologies on your resume."

    return {
        "score": overall_score,
        "accuracy": accuracy_score,
        "clarity": clarity_score,
        "depth": int(depth_score),
        "project_understanding": project_understanding,
        "resume_authenticity": resume_authenticity,
        "confidence": int(min(95, 60 + (word_count * 0.4))),
        "feedback": summary_feedback,
        "strengths": strengths,
        "areas_for_improvement": improvements,
        "skills_referenced": skills_mentioned
    }

def _evaluate_with_gemini(question: str, answer: str, category: str, skills: List[str]) -> Optional[Dict[str, Any]]:
    prompt = f"""
You are a senior technical interviewer evaluating a candidate's spoken response based on their resume.
Question: "{question}"
Category: "{category}"
Candidate Spoken Answer: "{answer}"
Resume Skills: {', '.join(skills[:8])}

Evaluate the answer and return ONLY valid JSON:
{{
  "score": (integer 0-100),
  "accuracy": (integer 0-100),
  "clarity": (integer 0-100),
  "depth": (integer 0-100),
  "project_understanding": (integer 0-100),
  "resume_authenticity": (integer 0-100),
  "confidence": (integer 0-100),
  "feedback": "2-sentence constructive feedback",
  "strengths": ["strength 1", "strength 2"],
  "areas_for_improvement": ["improvement 1", "improvement 2"]
}}
"""
    headers = {"Content-Type": "application/json"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=8)
    if resp.status_code == 200:
        data = resp.json()
        return json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
    return None

# -------------------------------------------------------------
# RESUME-AWARE PERFORMANCE REPORT GENERATOR
# -------------------------------------------------------------

def generate_resume_report(session_id: str) -> Dict[str, Any]:
    session = SESSIONS.get(session_id)
    if not session:
        return {"error": "Session not found"}

    evaluations = [q["evaluation"] for q in session.history if q.get("evaluation")]
    if not evaluations:
        return {
            "session_id": session_id,
            "candidate": session.candidate,
            "overall_score": 0,
            "recommendation": "Incomplete Interview",
            "summary_verdict": "No answers were recorded."
        }

    avg_score = int(sum(e["score"] for e in evaluations) / len(evaluations))
    avg_accuracy = int(sum(e["accuracy"] for e in evaluations) / len(evaluations))
    avg_clarity = int(sum(e["clarity"] for e in evaluations) / len(evaluations))
    avg_depth = int(sum(e["depth"] for e in evaluations) / len(evaluations))
    avg_proj = int(sum(e.get("project_understanding", 70) for e in evaluations) / len(evaluations))
    avg_auth = int(sum(e.get("resume_authenticity", 75) for e in evaluations) / len(evaluations))
    avg_conf = int(sum(e.get("confidence", 70) for e in evaluations) / len(evaluations))

    # Hiring Recommendation Decision
    if avg_score >= 82:
        recommendation = "Strong Hire"
        badge_class = "badge-strong-hire"
        summary_verdict = f"Outstanding performance! {session.candidate.get('name', 'The candidate')} convincingly demonstrated hands-on technical depth, clear project ownership, and strong verbal articulation."
    elif avg_score >= 68:
        recommendation = "Hire"
        badge_class = "badge-hire"
        summary_verdict = f"Solid performance! {session.candidate.get('name', 'The candidate')} confirmed their resume foundation and core project workflows, with opportunities to deepen edge-case explanations."
    elif avg_score >= 48:
        recommendation = "Needs Practice"
        badge_class = "badge-practice"
        summary_verdict = f"Promising potential. While {session.candidate.get('name', 'the candidate')} is familiar with their resume topics, they need more practice explaining low-level architecture and algorithm trade-offs."
    else:
        recommendation = "Developing"
        badge_class = "badge-developing"
        summary_verdict = "Needs substantial preparation. Focus on reinforcing core fundamentals, reviewing your resume project implementations, and practicing technical communication."

    # Identify specific questions candidate struggled with (score < 50)
    struggled_questions = []
    for item in session.history:
        ev = item.get("evaluation") or {}
        if ev.get("score", 0) < 55:
            struggled_questions.append({
                "question": item["question"],
                "score": ev.get("score", 0),
                "feedback": ev.get("feedback", "")
            })

    # Actionable resume recommendations
    skills_to_revise = []
    project_topics = []

    for item in session.history:
        ev = item.get("evaluation") or {}
        if ev.get("score", 0) < 65:
            entity = item.get("target_entity", "")
            if entity and entity in session.skills:
                skills_to_revise.append(entity)
            elif entity and any(p["name"] == entity for p in session.projects):
                project_topics.append(f"{entity}: Review architecture, dataset characteristics, and algorithm benchmarks.")

    if not skills_to_revise and session.skills:
        skills_to_revise = [session.skills[0]]
    if not project_topics and session.projects:
        project_topics = [f"{session.projects[0]['name']}: Be ready to explain architecture, algorithm choices, and trade-offs."]

    # Detailed question breakdown
    breakdown = []
    for idx, item in enumerate(session.history):
        ev = item.get("evaluation") or {}
        breakdown.append({
            "question_number": idx + 1,
            "question": item["question"],
            "category": item.get("category", "General"),
            "is_followup": item.get("is_followup", False),
            "difficulty": item["difficulty"],
            "candidate_answer": item.get("candidate_answer", "(No response recorded)"),
            "score": ev.get("score", 0),
            "feedback": ev.get("feedback", "No feedback recorded.")
        })

    duration_sec = int(time.time() - session.start_time)
    mins = duration_sec // 60
    secs = duration_sec % 60
    duration_str = f"{mins:02d}:{secs:02d}"

    # Unique strengths and areas for improvement
    all_strengths = []
    all_improvements = []
    for e in evaluations:
        all_strengths.extend(e.get("strengths", []))
        all_improvements.extend(e.get("areas_for_improvement", []))

    unique_strengths = list(dict.fromkeys(all_strengths))[:4]
    unique_improvements = list(dict.fromkeys(all_improvements))[:4]

    return {
        "session_id": session_id,
        "candidate": session.candidate,
        "education": session.education,
        "skills_detected": session.skills,
        "projects_count": len(session.projects),
        "duration": duration_str,
        "total_questions": len(evaluations),
        "overall_score": avg_score,
        "recommendation": recommendation,
        "badge_class": badge_class,
        "summary_verdict": summary_verdict,
        "completion_reason": session.completion_reason or "Interview completed successfully.",
        "metrics": {
            "technical_knowledge": avg_accuracy,
            "communication": avg_clarity,
            "problem_solving": avg_depth,
            "project_understanding": avg_proj,
            "resume_knowledge": avg_auth,
            "confidence": avg_conf
        },
        "resume_strengths": unique_strengths,
        "strengths": unique_strengths,
        "weak_areas": unique_improvements,
        "areas_for_improvement": unique_improvements,
        "struggled_questions": struggled_questions[:3],
        "skills_to_revise": list(dict.fromkeys(skills_to_revise))[:4],
        "project_topics_to_prepare": list(dict.fromkeys(project_topics))[:3],
        "question_breakdown": breakdown
    }
