from flask import Flask, request, redirect, session, send_file, jsonify, render_template
import os
import json
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from openai import OpenAI

# ---------- APP SETUP ----------
app = Flask(__name__)
app.secret_key = "secret123"

# ---------- OPENAI CLIENT ----------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_ai(prompt):
    """Call OpenAI API to generate text from prompt"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

# ---------- JSON DATABASE ----------
USERS_FILE = "users.json"
PROFILE_FILE = "profile.json"
HISTORY_FILE = "history.json"

def load_json(file):
    if os.path.exists(file):
        with open(file) as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ---------- JOB DATABASE ----------
JOB_DATABASE = {
    "Data Scientist": ["Python", "Machine Learning", "SQL"],
    "Web Developer": ["HTML", "CSS", "JavaScript"],
    "AI Engineer": ["Python", "Deep Learning"],
    "Cloud Engineer": ["AWS", "Docker"],
    "Cybersecurity Analyst": ["Networking", "Ethical Hacking"],
    "Software Engineer": ["Java", "Python", "DSA"]
}

def calculate_score(user_skills, role):
    """Calculate skill match percentage and missing skills"""
    required = JOB_DATABASE.get(role, [])
    user = [s.lower() for s in user_skills]
    matched = sum(1 for r in required if any(r.lower() in u for u in user))
    score = (matched / len(required)) * 100 if required else 0
    missing = [r for r in required if not any(r.lower() in u for u in user)]
    return round(score, 2), missing

# ---------- ROUTES ----------
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    users = load_json(USERS_FILE)
    error = None
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if users.get(u) == p:
            session['user'] = u
            return redirect('/dashboard')
        else:
            error = "Invalid login"
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    users = load_json(USERS_FILE)
    error = None
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        if u in users:
            error = "User exists"
        else:
            users[u] = p
            save_json(USERS_FILE, users)
            return redirect('/login')
    return render_template('register.html', error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    profiles = load_json(PROFILE_FILE)
    user_profile = profiles.get(session['user'], {
        "name": "",
        "phone": "",
        "email": "",
        "job": "",
        "skills": "",
        "experience": "",
        "projects": "",
        "education": "",
        "summary": ""
    })

    if request.method == 'POST':
        data = request.form.to_dict()
        session['data'] = data

        profiles[session['user']] = data
        save_json(PROFILE_FILE, profiles)

        return redirect('/result')

    # Pass 'profile' to the template, not 'data'
    return render_template('dashboard.html', profile=user_profile)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user' not in session:
        return redirect('/login')

    users_profiles = load_json(PROFILE_FILE)
    user_profile = users_profiles.get(session['user'], {
        "name": "",
        "phone": "",
        "email": "",
        "job": "",
        "skills": "",
        "experience": "",
        "projects": "",
        "education": "",
        "summary": ""
    })

    if request.method == 'POST':
        data = request.form.to_dict()
        users_profiles[session['user']] = data
        save_json(PROFILE_FILE, users_profiles)
        return render_template('profile.html', profile=data, user=session['user'], saved=True)

    return render_template('profile.html', profile=user_profile, user=session['user'], saved=False)

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')

    # Load all resume histories
    histories = load_json(HISTORY_FILE)  # HISTORY_FILE = path to your JSON storing resumes

    # Get only the logged-in user's entries
    user_entries = histories.get(session['user'], [])

    # Sort by date descending and take last 10
    user_entries = sorted(user_entries, key=lambda x: x.get('date', ''), reverse=True)[:10]

    return render_template('history.html', entries=user_entries)
def generate_summary():
    prompt = f"""
Create a professional resume summary:

Name: {request.form.get('name', '')}
Role: {request.form.get('job', '')}
Skills: {request.form.get('skills', '')}
Experience: {request.form.get('experience', '')}
Projects: {request.form.get('projects', '')}
Education: {request.form.get('education', '')}
"""
    summary = call_ai(prompt)
    return jsonify({"summary": summary})

@app.route('/result')
def result():
    data = session.get('data')
    if not data:
        return redirect('/dashboard')
    skills = [s.strip() for s in data['skills'].split(',')]
    score, missing = calculate_score(skills, data['job'])

    # Save history
    history = load_json(HISTORY_FILE)
    history.setdefault(session['user'], []).append(data)
    save_json(HISTORY_FILE, history)

    return render_template('result.html', data=data, score=score, missing=missing)

@app.route('/download')
def download():
    data = session.get('data')
    if not data:
        return redirect('/dashboard')
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph(f"Name: {data.get('name', '')}", styles['Heading2']),
        Paragraph(f"Role: {data.get('job', '')}", styles['Heading3']),
        Paragraph(f"Skills: {data.get('skills', '')}", styles['Normal']),
        Paragraph(f"Experience: {data.get('experience', '')}", styles['Normal'])
    ]
    doc.build(story)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="resume.pdf")

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')
# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
