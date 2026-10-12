import re
import os
import json
from typing import Dict, Any, List, Optional
import pymupdf  # PyMuPDF / fitz
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extracts plain text from all pages of a PDF in memory using PyMuPDF.
    Validates file headers and ensures readable text is present.
    """
    if not pdf_bytes:
        raise ValueError("Uploaded file is empty.")

    # Validate PDF signature
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Invalid file format. Please upload a valid PDF document.")

    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open PDF file: {str(e)}")

    if len(doc) == 0:
        raise ValueError("The uploaded PDF has no pages.")

    full_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            full_text.append(text.strip())

    combined_text = "\n\n".join(full_text).strip()

    if len(combined_text) < 30:
        raise ValueError(
            "The uploaded PDF does not contain sufficient extractable text. "
            "It may be a scanned image. Please upload a text-based resume PDF."
        )

    return combined_text

def analyze_resume(resume_text: str) -> Dict[str, Any]:
    """
    Analyzes resume text to extract candidate info, skills, projects,
    education, certifications, and experience.
    Uses Gemini API if key is set; otherwise uses advanced local heuristic NLP parser.
    """
    if GEMINI_API_KEY:
        try:
            llm_result = _analyze_with_gemini(resume_text)
            if llm_result and "skills" in llm_result:
                return llm_result
        except Exception as e:
            print(f"[Resume Analysis] Gemini fallback to local parser: {e}")

    return _analyze_locally(resume_text)

def _analyze_locally(resume_text: str) -> Dict[str, Any]:
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    lower_text = resume_text.lower()

    # 1. Candidate Name (usually in top lines)
    name = "Candidate"
    for line in lines[:5]:
        cleaned = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = cleaned.split()
        if 2 <= len(words) <= 4:
            if not any(k in cleaned.lower() for k in ["resume", "curriculum", "vitae", "contact", "email", "phone", "linkedin", "github"]):
                name = cleaned.title()
                break

    # 2. Candidate Contact & Links
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', resume_text)
    email = email_match.group(0) if email_match else ""

    # 3. Education Extraction
    degree = "B.Tech"
    if re.search(r'\bb\.?\s*tech\b', lower_text):
        degree = "B.Tech"
    elif re.search(r'\bb\.?\s*e\b', lower_text):
        degree = "B.E"
    elif re.search(r'\bm\.?\s*tech\b', lower_text):
        degree = "M.Tech"
    elif re.search(r'\bb\.?\s*s\b|bachelor of science', lower_text):
        degree = "B.S."
    elif re.search(r'\bm\.?\s*s\b|master of science', lower_text):
        degree = "M.S."
    elif re.search(r'\bmca\b', lower_text):
        degree = "MCA"

    branch = "Computer Science"
    if "computer science" in lower_text or "cse" in lower_text:
        branch = "Computer Science & Engineering"
    elif "information technology" in lower_text or "\bit\b" in lower_text:
        branch = "Information Technology"
    elif "electronics" in lower_text or "ece" in lower_text:
        branch = "Electronics & Communication"
    elif "data science" in lower_text:
        branch = "Data Science"
    elif "artificial intelligence" in lower_text or "\bai\b" in lower_text:
        branch = "Artificial Intelligence"

    college = "University"
    college_match = re.search(r'([A-Z][a-zA-Z0-9\t ,\.\'-]+(?:University|College|Institute|Campus|Academy)[a-zA-Z0-9\t ,\.\'-]*)', resume_text)
    if college_match:
        college = college_match.group(1).split("\n")[0].strip()
        college = re.split(r'[,|]\s*(?:Class of|\d{4}|\bCGPA\b|\bGPA\b)', college)[0].strip()
    else:
        for line in lines:
            if any(w in line.lower() for w in ["institute", "university", "college", "engineering"]):
                if len(line.split()) < 8:
                    college = line.strip()
                    break

    grad_year = "2025"
    year_matches = re.findall(r'\b(20[12][0-9])\b', resume_text)
    if year_matches:
        # Choose the latest year found
        valid_years = [int(y) for y in year_matches if 2018 <= int(y) <= 2030]
        if valid_years:
            grad_year = str(max(valid_years))

    cgpa = ""
    cgpa_match = re.search(r'(\d+\.\d+)\s*(?:/10|/4|cgpa|gpa)', lower_text)
    if cgpa_match:
        cgpa = cgpa_match.group(1) + " CGPA"

    # 4. Open-vocabulary Technical Skills Detection
    SKILL_DICTIONARY = [
        # Languages
        "Python", "Java", "C++", "C#", "C", "JavaScript", "TypeScript", "Go", "Golang", "Rust", "Ruby", "PHP",
        "Swift", "Kotlin", "SQL", "HTML", "HTML5", "CSS", "CSS3", "Bash", "Shell", "R", "Scala", "Dart",
        # Frameworks & Libraries
        "React", "React.js", "Angular", "Vue", "Vue.js", "Next.js", "Node.js", "Express", "Express.js",
        "Flask", "Django", "FastAPI", "Spring", "Spring Boot", "OpenCV", "TensorFlow", "PyTorch", "Scikit-Learn",
        "Pandas", "NumPy", "Keras", "Matplotlib", "Seaborn", "Tailwind CSS", "Bootstrap", "jQuery",
        # Databases & Cache
        "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Redis", "Oracle", "Cassandra", "DynamoDB", "Firebase",
        # Cloud, DevOps & Tools
        "Git", "GitHub", "GitLab", "Docker", "Kubernetes", "AWS", "Amazon Web Services", "Azure", "GCP",
        "Google Cloud", "Linux", "CI/CD", "Jenkins", "Postman", "REST API", "GraphQL", "Microservices",
        # Domains & Concepts
        "Machine Learning", "Data Science", "Artificial Intelligence", "Deep Learning", "Computer Vision",
        "Natural Language Processing", "NLP", "OOP", "Object-Oriented Programming", "Data Structures",
        "Algorithms", "DBMS", "Computer Networks", "Operating Systems", "Agile", "Scrum"
    ]

    detected_skills_set = set()
    for skill in SKILL_DICTIONARY:
        if skill == "C":
            # Must be standalone 'C', not part of C++, C#, or lowercase 'c'
            if re.search(r'(?<![a-zA-Z0-9+#])C(?![a-zA-Z0-9+#])', resume_text):
                detected_skills_set.add(skill)
        elif skill == "R":
            # Must be standalone uppercase 'R'
            if re.search(r'(?<![a-zA-Z0-9])R(?![a-zA-Z0-9])', resume_text):
                detected_skills_set.add(skill)
        elif skill in ["C++", "C#"]:
            if re.search(r'(?<![a-zA-Z0-9])' + re.escape(skill) + r'(?![a-zA-Z0-9])', resume_text, re.IGNORECASE):
                detected_skills_set.add(skill)
        else:
            pattern = r'(?<![a-zA-Z0-9])' + re.escape(skill.lower()) + r'(?![a-zA-Z0-9])'
            if re.search(pattern, lower_text):
                detected_skills_set.add(skill)

    # Also inspect dedicated "SKILLS" section for custom/open-vocabulary skills
    skills_section_text = _extract_section(resume_text, ["skills", "technical skills", "skills & abilities", "technologies", "competencies"])
    if skills_section_text:
        # Split by commas, bullets, pipes, or newlines
        potential_skills = re.split(r'[,|•\n\t/]+', skills_section_text)
        for ps in potential_skills:
            item = ps.strip()
            # Clean prefixes like "Languages:", "Frameworks:", "Tools & Cloud:"
            item = re.sub(r'^[a-zA-Z\s&]+:\s*', '', item).strip()
            # Strip any leading bullets or symbols
            item = re.sub(r'^[\?\u2022\u25cf\u25cb\uf0b7•\-\*\s]+', '', item).strip()
            if item and 2 <= len(item) <= 25 and not any(k in item.lower() for k in ["tools", "languages", "frameworks", "libraries", "cloud"]):
                # Filter out full sentences
                if not re.search(r'\b(developed|worked|managed|experience|using|project|system)\b', item.lower()):
                    if item.istitle() or item.isupper() or any(c.isupper() for c in item):
                        detected_skills_set.add(item)

    detected_skills = sorted(list(detected_skills_set))
    if not detected_skills:
        detected_skills = ["Python", "SQL", "Problem Solving", "Data Structures"]

    # 5. Project Extraction
    projects = []
    projects_section_text = _extract_section(resume_text, ["projects", "academic projects", "personal projects", "key projects"])

    if projects_section_text:
        # Split project entries by bullet points, double newlines, or numbered lists
        project_blocks = re.split(r'\n(?=[•\-\*\d\.\?\u2022\u25cf\u25cb\uf0b7]\s+[A-Z])|\n\n+', projects_section_text)
        for block in project_blocks:
            block = block.strip()
            if len(block) > 25:
                block_lines = [l.strip() for l in block.splitlines() if l.strip()]
                title_line = block_lines[0]
                # Strip leading bullets and weird symbols
                title = re.sub(r'^[\?\u2022\u25cf\u25cb\uf0b7•\-\*\d\.\s]+', '', title_line)
                # If title contains tech stack separated by ( ) or | or -
                tech_match = re.search(r'\(([^)]+)\)\s*$', title) or re.search(r'\s+[|–\-]\s+([^\n]+)$', title)
                techs_found = []
                if tech_match:
                    tech_str = tech_match.group(1)
                    title = title[:tech_match.start()].strip()
                    techs_found = [t.strip() for t in re.split(r'[,/|]+', tech_str) if t.strip()]

                # Find technologies mentioned inside the block description
                for sk in detected_skills:
                    if sk.lower() in block.lower() and sk not in techs_found:
                        techs_found.append(sk)

                desc = " ".join(block_lines[1:]) if len(block_lines) > 1 else block_lines[0]

                # Extract claims
                claims = []
                for sentence in re.split(r'[.!?]+', block):
                    s = sentence.strip()
                    if any(w in s.lower() for w in [
                        "developed", "built", "implemented", "achieved", "designed", "trained",
                        "created", "reduced", "reducing", "increased", "increasing", "engineered",
                        "optimized", "optimizing", "automated", "automating", "architected",
                        "spearheaded", "integrated", "integrating", "deployed", "deploying"
                    ]):
                        clean_claim = " ".join(s.split())
                        if len(clean_claim) > 15 and clean_claim.lower() != title.lower():
                            claims.append(clean_claim)

                if len(title.split()) <= 8 and not title.lower().startswith("project"):
                    projects.append({
                        "name": title.strip(),
                        "description": desc[:280].strip(),
                        "technologies": techs_found[:5],
                        "claims": claims[:3]
                    })

    # If no projects could be parsed from sections, search full text for project mentions
    if not projects:
        proj_headings = re.findall(r'(?:project|developed|built|created)\s*:\s*([^\n\.]+)', resume_text, re.IGNORECASE)
        for ph in proj_headings[:2]:
            projects.append({
                "name": ph.strip().title(),
                "description": f"Engineered software system using {', '.join(detected_skills[:3])}.",
                "technologies": detected_skills[:3],
                "claims": [f"Implemented {ph.strip()} utilizing modern development practices."]
            })

    if not projects:
        # Default fallback project based on skills detected
        primary_skill = detected_skills[0] if detected_skills else "Python"
        projects.append({
            "name": f"{primary_skill} Web & Data Application",
            "description": f"Developed an end-to-end software application integrating {', '.join(detected_skills[:3])}.",
            "technologies": detected_skills[:3],
            "claims": [f"Built modular architecture using {primary_skill}."]
        })

    # 6. Certifications Extraction
    certs = []
    certs_section_text = _extract_section(resume_text, ["certifications", "certificates", "licenses", "courses", "trainings"])
    if certs_section_text:
        for line in certs_section_text.splitlines():
            line = re.sub(r'^[\?\u2022\u25cf\u25cb\uf0b7•\-\*\d\.\s]+', '', line).strip()
            if 6 <= len(line) <= 90 and not line.lower().startswith("certifi"):
                certs.append(line)

    # 7. Experience Extraction
    exp_summary = "No professional experience detected"
    exp_section_text = _extract_section(resume_text, ["experience", "work experience", "internships", "professional experience", "employment"])
    if exp_section_text and len(exp_section_text.strip()) > 30:
        first_exp_line = exp_section_text.splitlines()[0]
        first_exp_line = re.sub(r'^[\?\u2022\u25cf\u25cb\uf0b7•\-\*\d\.\s]+', '', first_exp_line).strip()
        exp_summary = first_exp_line if len(first_exp_line) < 100 else exp_section_text[:90] + "..."

    return {
        "candidate": {
            "name": name,
            "email": email,
            "college": college,
            "degree": degree,
            "branch": branch,
            "year": grad_year,
            "cgpa": cgpa
        },
        "education": f"{degree} in {branch}, {college} ({grad_year})",
        "skills": detected_skills,
        "projects": projects[:4],
        "certifications": certs[:4],
        "experience": exp_summary,
        "raw_text_length": len(resume_text)
    }

def _extract_section(text: str, section_headers: List[str]) -> str:
    """
    Extracts text between a specified section header and the next section header.
    """
    lines = text.splitlines()
    capturing = False
    captured_lines = []

    ALL_HEADERS = [
        "skills", "technical skills", "projects", "academic projects", "experience",
        "work experience", "education", "certifications", "achievements", "publications",
        "summary", "profile", "contact", "interests", "activities", "languages"
    ]

    for line in lines:
        stripped = line.strip().lower()
        clean_header = re.sub(r'[^a-zA-Z\s]', '', stripped).strip()

        # Check if this line is our target header
        if any(h == clean_header or clean_header.startswith(h + " ") for h in section_headers):
            capturing = True
            continue

        # Check if we hit another header
        if capturing:
            if any(h == clean_header or (len(clean_header.split()) <= 3 and clean_header.startswith(h)) for h in ALL_HEADERS if not any(sh in clean_header for sh in section_headers)):
                break
            captured_lines.append(line)

    return "\n".join(captured_lines).strip()

def _analyze_with_gemini(resume_text: str) -> Optional[Dict[str, Any]]:
    prompt = f"""
Analyze the following resume text. Extract candidate details, skills, projects with claims, education, certifications, and experience.
Return ONLY a valid JSON object matching this exact schema:
{{
  "candidate": {{
    "name": "Candidate Full Name",
    "email": "email@example.com",
    "college": "University / College Name",
    "degree": "Degree (e.g. B.Tech, B.S.)",
    "branch": "Branch/Major (e.g. Computer Science)",
    "year": "Graduation Year (e.g. 2025)",
    "cgpa": "CGPA or percentage if present, else empty"
  }},
  "education": "Brief degree & college summary",
  "skills": ["Skill1", "Skill2", "Skill3"],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Brief description of problem solved and architecture",
      "technologies": ["Tech1", "Tech2"],
      "claims": ["Specific achievement, algorithm, or feature claim"]
    }}
  ],
  "certifications": ["Certification 1"],
  "experience": "Brief summary of internships or 'No professional experience detected'"
}}

Resume Text:
{resume_text[:6000]}
"""
    headers = {"Content-Type": "application/json"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=12)
    if resp.status_code == 200:
        data = resp.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw)
    return None
