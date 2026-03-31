from flask import Flask, request, redirect, session, send_file, jsonify, render_template
import requests
import os
import json
from io import BytesIO
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
 
app = Flask(__name__)
app.secret_key = "secret123"
 
# ---------- FILE PATHS ----------
USERS_FILE    = "users.json"
PROFILES_FILE = "profiles.json"
HISTORY_FILE  = "history.json"
 
# ---------- DATA HELPERS ----------
def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath) as f:
            return json.load(f)
    return {}
 
def save_json(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)
 
def get_profile(username):
    profiles = load_json(PROFILES_FILE)
    return profiles.get(username, {
        'name': '', 'email': '', 'phone': '', 'job': '',
        'skills': '', 'education': '', 'experience': '',
        'projects': '', 'summary': ''
    })
 
def save_profile(username, profile_data):
    profiles = load_json(PROFILES_FILE)
    profiles[username] = profile_data
    save_json(PROFILES_FILE, profiles)
 
def get_history(username):
    history = load_json(HISTORY_FILE)
    return history.get(username, [])
 
def save_history_entry(username, entry):
    history = load_json(HISTORY_FILE)
    if username not in history:
        history[username] = []
    history[username].insert(0, entry)   # newest first
    history[username] = history[username][:10]  # keep last 10
    save_json(HISTORY_FILE, history)
 
# ---------- JOB DATABASE ----------
JOB_DATABASE = {
    "Data Scientist":    ["Python", "Machine Learning", "SQL"],
    "Web Developer":     ["HTML", "CSS", "JavaScript"],
    "AI Engineer":       ["Python", "Deep Learning"],
    "Data Analyst":      ["SQL", "Excel", "Python"],
    "Backend Developer": ["Python", "REST API", "SQL"],
}
 
# ---------- OLLAMA ----------
def call_ollama(prompt):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False},
            timeout=180
        )
        if response.status_code != 200:
            return "❌ Ollama Error: " + response.text
        return response.json().get("response", "No response from AI")
    except requests.exceptions.ConnectionError:
        return "❌ Ollama NOT running. Run: ollama serve"
    except Exception as e:
        return "❌ Error: " + str(e)
 
# ---------- HELPERS ----------
def generate_summary(name, role):
    return f"{name} is an aspiring {role} with strong technical skills."
 
def calculate_score(user_skills, role):
    required = JOB_DATABASE.get(role, [])
    user = [s.strip().lower() for s in user_skills]
    matched = len(set(user).intersection([r.lower() for r in required]))
    score = (matched / len(required)) * 100 if required else 0
    missing = [r for r in required if r.lower() not in user]
    return round(score, 2), missing
 
# ---------- HOME ----------
@app.route('/')
def home():
    return render_template('home.html')
 
# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        users = load_json(USERS_FILE)
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if users.get(username) == password:
            session['user'] = username
            return redirect('/dashboard')
        else:
            error = "Invalid username or password."
    return render_template('login.html', error=error)
 
# ---------- REGISTER ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        users = load_json(USERS_FILE)
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username in users:
            error = "Username already exists."
        else:
            users[username] = password
            save_json(USERS_FILE, users)
            return redirect('/login')
    return render_template('register.html', error=error)
 
# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')
 
# ---------- PROFILE ----------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        return redirect('/login')
    username = session['user']
    saved = False
    if request.method == 'POST':
        profile_data = {
            'name':       request.form.get('name', ''),
            'email':      request.form.get('email', ''),
            'phone':      request.form.get('phone', ''),
            'job':        request.form.get('job', ''),
            'skills':     request.form.get('skills', ''),
            'education':  request.form.get('education', ''),
            'experience': request.form.get('experience', ''),
            'projects':   request.form.get('projects', ''),
            'summary':    request.form.get('summary', ''),
        }
        save_profile(username, profile_data)
        saved = True
    profile_data = get_profile(username)
    return render_template('profile.html', user=username,
                           profile=profile_data, saved=saved)
 
# ---------- DASHBOARD ----------
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    username = session['user']
 
    if request.method == 'POST':
        data = {
            'name':       request.form.get('name', ''),
            'email':      request.form.get('email', ''),
            'phone':      request.form.get('phone', ''),
            'job':        request.form.get('job', ''),
            'summary':    request.form.get('summary', ''),
            'skills':     request.form.get('skills', ''),
            'experience': request.form.get('experience', ''),
            'projects':   request.form.get('projects', ''),
            'education':  request.form.get('education', ''),
        }
        session['data'] = data
 
        # Auto-save to profile (keeps common fields updated)
        profile_data = get_profile(username)
        for key in ['name', 'email', 'phone', 'job', 'skills', 'education']:
            if data.get(key):
                profile_data[key] = data[key]
        save_profile(username, profile_data)
 
        return redirect('/result')
 
    # Pre-fill form from saved profile
    profile_data = get_profile(username)
    return render_template('dashboard.html', user=username, profile=profile_data)
 
# ---------- HISTORY ----------
@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')
    entries = get_history(session['user'])
    return render_template('history.html', user=session['user'], entries=entries)
 
# ---------- RESULT ----------
@app.route('/result')
def result():
    if 'user' not in session:
        return redirect('/login')
    data = session.get('data')
    if not data:
        return redirect('/dashboard')
 
    skill_list = [s.strip() for s in data['skills'].split(',') if s.strip()]
    score, missing = calculate_score(skill_list, data['job'])
    summary = generate_summary(data['name'], data['job'])
 
    # Save to history
    save_history_entry(session['user'], {
        'date':    datetime.now().strftime("%d %b %Y, %I:%M %p"),
        'name':    data['name'],
        'job':     data['job'],
        'score':   score,
        'missing': missing,
        'skills':  data['skills'],
    })
 
    return render_template('result.html', data=data, score=score,
                           missing=missing, summary=summary)
 
# ---------- GENERATE SUMMARY AI ----------
@app.route('/generate_summary', methods=['POST'])
def generate_summary_ai():
    name       = request.form.get('name', '')
    job        = request.form.get('job', '')
    skills     = request.form.get('skills', '')
    experience = request.form.get('experience', '')
    projects   = request.form.get('projects', '')
    education  = request.form.get('education', '')
 
    prompt = f"""Write a professional resume summary paragraph for this candidate.
Name: {name}
Target Role: {job}
Skills: {skills}
Experience: {experience}
Projects: {projects}
Education: {education}
 
Instructions:
- Write 3-5 sentences only
- Be specific to their actual skills and experience
- Use strong professional language
- Do NOT include headers, bullet points, or labels
- Output ONLY the summary paragraph, nothing else
"""
    summary = call_ollama(prompt)
    return jsonify({"summary": summary})
 
# ---------- CHAT ----------
@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.form.get('msg', '').strip()
    if not user_msg:
        return jsonify({"reply": "⚠️ Empty message"})
 
    data = session.get('data', {})
    skills = data.get('skills', '')
    role   = data.get('job', '')
    name   = data.get('name', '')
    skill_list = [s.strip() for s in skills.split(',') if s.strip()]
    score, missing = calculate_score(skill_list, role)
 
    prompt = f"""You are a professional resume coach and career advisor.
Candidate Name: {name}
Target Role: {role}
Skills: {skills}
Resume Score: {score}%
Missing Skills: {', '.join(missing) if missing else 'None'}
User Question: {user_msg}
Give practical, specific, short advice (3-5 sentences max)."""
 
    reply = call_ollama(prompt)
    return jsonify({"reply": reply})
 
# ---------- DOWNLOAD PDF ----------
@app.route('/download')
def download():
    if 'user' not in session:
        return redirect('/login')
    data = session.get('data')
    if not data:
        return redirect('/dashboard')
 
    skill_list = [s.strip() for s in data['skills'].split(',') if s.strip()]
    score, missing = calculate_score(skill_list, data['job'])
 
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    heading = ParagraphStyle('H', fontSize=16, fontName='Helvetica-Bold', spaceAfter=4)
    sub     = ParagraphStyle('S', fontSize=12, fontName='Helvetica-Bold', spaceAfter=2)
    normal  = styles['Normal']
 
    story = []
    story.append(Paragraph(data['name'], heading))
    story.append(Paragraph(f"{data['email']}  |  {data['phone']}", normal))
    story.append(Paragraph(f"Target Role: {data['job']}", normal))
    story.append(Spacer(1, 12))
 
    for title, key in [("Professional Summary", "summary"), ("Skills", "skills"),
                       ("Experience", "experience"), ("Projects", "projects"),
                       ("Education", "education")]:
        if data.get(key, '').strip():
            story.append(Paragraph(title, sub))
            story.append(Paragraph(data[key].replace('\n', '<br/>'), normal))
            story.append(Spacer(1, 10))
 
    story.append(Paragraph(f"ATS Score: {score}%", sub))
    if missing:
        story.append(Paragraph(f"Missing Skills: {', '.join(missing)}", normal))
 
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True,
                     download_name=f"{data['name'].replace(' ', '_')}_resume.pdf",
                     mimetype='application/pdf')
 
# ---------- CREATE RESUME ----------
@app.route('/create_resume', methods=['GET', 'POST'])
def create_resume():
    if 'user' not in session:
        return redirect('/login')
    saved = False
    if request.method == 'POST':
        session['resume_content'] = request.form.get('content', '')
        saved = True
    return render_template('create_resume.html', saved=saved,
                           content=session.get('resume_content', ''))
 
# ---------- TEST ----------
@app.route('/test')
def test():
    return call_ollama("Say hello in one line")
 
if __name__ == '__main__':
    app.run(debug=True)