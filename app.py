import os
import re
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS

from database import (
    init_db,
    register_user,
    authenticate_user,
    get_user_by_id,
    save_interview_record,
    get_user_interviews,
    get_interview_report_by_session
)
from resume_parser import extract_text_from_pdf, analyze_resume
from interview_engine import (
    start_resume_interview,
    process_resume_answer,
    generate_resume_report,
    SESSIONS
)

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

# Session Security Configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ai-interview-room-auth-secret-key-2026")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=14)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB maximum PDF upload

# Ensure database is initialized
init_db()

# -------------------------------------------------------------
# AUTHENTICATION DECORATOR & GUARDS
# -------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please log in."}), 401
            return redirect(url_for("login", next=request.full_path if request.method == 'GET' else url_for('dashboard')))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------------------------------------
# PUBLIC ROUTES
# -------------------------------------------------------------

@app.route("/")
def index():
    """Landing page - displays Login/Signup buttons and features."""
    return render_template("landing.html")

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "AI Interview Room", "auth": "enabled"})

# -------------------------------------------------------------
# AUTHENTICATION ROUTES (SIGNUP, LOGIN, LOGOUT)
# -------------------------------------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Validation
        if not full_name:
            return render_template("signup.html", error="Full name is required.", full_name=full_name, email=email)
        if not email or "@" not in email or "." not in email:
            return render_template("signup.html", error="A valid email address is required.", full_name=full_name, email=email)
        if len(password) < 8:
            return render_template("signup.html", error="Password must be at least 8 characters long.", full_name=full_name, email=email)
        if password != confirm_password:
            return render_template("signup.html", error="Passwords do not match.", full_name=full_name, email=email)

        result = register_user(full_name, email, password)
        if result["success"]:
            user = result["user"]
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_email"] = user["email"]
            flash(f"Welcome to AI Interview Room, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            return render_template("signup.html", error=result["error"], full_name=full_name, email=email)

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    next_url = request.args.get("next") or request.form.get("next") or ""

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        remember_me = request.form.get("remember_me")

        if not email or not password:
            return render_template("login.html", error="Please enter both email and password.", email=email, next_url=next_url)

        user = authenticate_user(email, password)
        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["user_email"] = user["email"]
            if remember_me:
                session.permanent = True

            flash("Successfully logged in.", "success")
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid email or password.", email=email, next_url=next_url)

    return render_template("login.html", next_url=next_url)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

# -------------------------------------------------------------
# PROTECTED PAGES
# -------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    """Personalized user dashboard displaying stats and previous interviews."""
    user = get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("login"))

    interviews = get_user_interviews(user["id"])
    return render_template("dashboard.html", user=user, interviews=interviews)

@app.route("/interview")
@login_required
def interview():
    """Protected resume upload, analysis confirmation, and virtual room suite."""
    return render_template("interview.html")

# Private redirect aliases for backward compatibility and clean routing
@app.route("/resume")
@app.route("/profile")
@app.route("/history")
@login_required
def private_dashboard_redirect():
    return redirect(url_for("dashboard"))

@app.route("/report")
@login_required
def report_redirect():
    return redirect(url_for("dashboard"))

# -------------------------------------------------------------
# PROTECTED API ENDPOINTS
# -------------------------------------------------------------

@app.route("/api/resume/upload", methods=["POST"])
@login_required
def upload_resume():
    """
    Receives uploaded PDF resume, extracts text with PyMuPDF,
    analyzes skills, projects, and background, and returns structured resume profile.
    """
    if 'resume' not in request.files:
        return jsonify({"error": "No resume file provided. Please upload a PDF file."}), 400

    file = request.files['resume']
    if not file or file.filename == '':
        return jsonify({"error": "No file selected."}), 400

    if not file.filename.lower().endswith('.pdf'):
        return jsonify({"error": "Invalid file type. Please upload a PDF file (.pdf)."}), 400

    try:
        pdf_bytes = file.read()
        if len(pdf_bytes) == 0:
            return jsonify({"error": "Uploaded file is empty."}), 400

        # Extract text via PyMuPDF
        resume_text = extract_text_from_pdf(pdf_bytes)

        # Analyze resume
        analysis_result = analyze_resume(resume_text)

        # If candidate name was generic, default to user's registered name
        if analysis_result.get("candidate", {}).get("name") in ["Candidate", ""]:
            analysis_result["candidate"]["name"] = session.get("user_name", "Candidate")

        return jsonify({
            "success": True,
            "filename": file.filename,
            "resume_data": analysis_result
        }), 200

    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to process resume: {str(e)}"}), 500

@app.route("/api/interview/start", methods=["POST"])
@login_required
def start_interview():
    """Initializes a resume-driven interview session."""
    try:
        data = request.get_json() or {}
        resume_data = data.get("resume_data")

        if not resume_data:
            user_name = session.get("user_name", "Candidate")
            resume_data = {
                "candidate": {"name": user_name, "college": "University", "branch": "Computer Science", "year": "2025"},
                "education": "Degree in Computer Science",
                "skills": ["Python", "SQL", "Problem Solving"],
                "projects": [{"name": "Software Application", "description": "Developed software project.", "technologies": ["Python"], "claims": ["Built modular application."]}]
            }

        result = start_resume_interview(resume_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/interview/submit-answer", methods=["POST"])
@login_required
def submit_answer():
    """Processes candidate's transcribed verbal answer."""
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        answer = data.get("answer", "").strip()

        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400

        result = process_resume_answer(session_id, answer)

        # If interview completed during this answer, save to database
        if result.get("is_completed"):
            report = generate_resume_report(session_id)
            save_interview_record(
                user_id=session["user_id"],
                session_id=session_id,
                candidate_name=report.get("candidate", {}).get("name", session.get("user_name")),
                interview_type="Resume-Driven Interview",
                overall_score=report.get("overall_score", 0),
                recommendation=report.get("recommendation", "Completed"),
                duration=report.get("duration", "05:00"),
                report_dict=report
            )

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/interview/end", methods=["POST"])
@login_required
def end_interview():
    """Concludes the interview and saves performance report to user's history."""
    try:
        data = request.get_json() or {}
        session_id = data.get("session_id")
        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400

        if session_id in SESSIONS:
            sess = SESSIONS[session_id]
            sess.is_completed = True
            if not sess.completion_reason:
                sess.completion_reason = "Interview concluded by candidate."

        report = generate_resume_report(session_id)
        if "error" in report:
            # Check if stored in DB
            db_report = get_interview_report_by_session(session_id, session["user_id"])
            if db_report:
                return jsonify(db_report), 200
            return jsonify(report), 404

        # Persist to SQLite
        save_interview_record(
            user_id=session["user_id"],
            session_id=session_id,
            candidate_name=report.get("candidate", {}).get("name", session.get("user_name")),
            interview_type="Resume-Driven Interview",
            overall_score=report.get("overall_score", 0),
            recommendation=report.get("recommendation", "Completed"),
            duration=report.get("duration", "05:00"),
            report_dict=report
        )

        return jsonify(report), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/interview/report/<session_id>", methods=["GET"])
@login_required
def get_report(session_id):
    """Retrieves full interview report from active memory or SQLite database."""
    try:
        # Check active in-memory session
        if session_id in SESSIONS:
            report = generate_resume_report(session_id)
            # Ensure saved to DB
            save_interview_record(
                user_id=session["user_id"],
                session_id=session_id,
                candidate_name=report.get("candidate", {}).get("name", session.get("user_name")),
                interview_type="Resume-Driven Interview",
                overall_score=report.get("overall_score", 0),
                recommendation=report.get("recommendation", "Completed"),
                duration=report.get("duration", "05:00"),
                report_dict=report
            )
            return jsonify(report), 200

        # Check SQLite DB
        db_report = get_interview_report_by_session(session_id, session["user_id"])
        if db_report:
            return jsonify(db_report), 200

        return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/user/history", methods=["GET"])
@login_required
def user_history():
    """Returns past interview sessions for the logged-in user."""
    interviews = get_user_interviews(session["user_id"])
    return jsonify({"interviews": interviews}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"* AI Interview Room running on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
