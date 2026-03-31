from flask import Flask, request, redirect, session, send_file, jsonify, render_template
import os
import json
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
import openai

app = Flask(__name__)
app.secret_key = "secret123"

# ✅ ADD YOUR API KEY HERE
openai.api_key = "YOUR_OPENAI_API_KEY"

# ---------- DATABASE ----------
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

JOB_DATABASE = {
    "Data Scientist": ["Python", "Machine Learning", "SQL", "Pandas", "NumPy", "Data Visualization"],
    "Data Analyst": ["Excel", "SQL", "Python", "Power BI", "Tableau"],
    "Web Developer": ["HTML", "CSS", "JavaScript", "React", "Node.js"],
    "Frontend Developer": ["HTML", "CSS", "JavaScript", "React", "UI/UX"],
    "Backend Developer": ["Python", "Node.js", "Django", "Flask", "SQL"],
    "Full Stack Developer": ["HTML", "CSS", "JavaScript", "React", "Node.js", "MongoDB"],
    "AI Engineer": ["Python", "Deep Learning", "TensorFlow", "PyTorch"],
    "Machine Learning Engineer": ["Python", "Scikit-learn", "TensorFlow", "ML Algorithms"],
    "Cloud Engineer": ["AWS", "Azure", "Docker", "Kubernetes"],
    "DevOps Engineer": ["Docker", "Kubernetes", "CI/CD", "Jenkins", "Linux"],
    "Cybersecurity Analyst": ["Networking", "Ethical Hacking", "Cryptography"],
    "Mobile App Developer": ["Java", "Kotlin", "Flutter", "React Native"],
    "Software Engineer": ["Java", "Python", "OOP", "DSA"],
}

# ---------- OPENAI FUNCTION ----------
def call_ai(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional resume coach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return "❌ API Error: " + str(e)

# ---------- FUNCTIONS ----------
def generate_summary(name, role):
    return f"{name} is an aspiring {role} with strong technical skills."

def calculate_score(user_skills, role):
    required = JOB_DATABASE.get(role, [])
    user = [s.strip().lower() for s in user_skills]
    matched = len(set(user).intersection([r.lower() for r in required]))
    score = (matched / len(required)) * 100 if required else 0
    missing = [r for r in required if r.lower() not in user]
    return round(score, 2), missing

# ---------- ROUTES ----------

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        users = load_users()
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if users.get(username) == password:
            session['user'] = username
            return redirect('/dashboard')
        else:
            error = "Invalid username or password."
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        users = load_users()
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username in users:
            error = "Username already exists."
        else:
            users[username] = password
            save_users(users)
            return redirect('/login')
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        session['data'] = {
            'name': request.form.get('name', ''),
            'email': request.form.get('email', ''),
            'phone': request.form.get('phone', ''),
            'job': request.form.get('job', ''),
            'skills': request.form.get('skills', ''),
            'experience': request.form.get('experience', ''),
            'projects': request.form.get('projects', ''),
            'education': request.form.get('education', ''),
            'summary': request.form.get('summary', '')
        }
        return redirect('/result')

    return render_template('dashboard.html', user=session['user'], profile={})

@app.route('/generate_summary', methods=['POST'])
def generate_summary_ai():
    name = request.form.get('name', '')
    job = request.form.get('job', '')
    skills = request.form.get('skills', '')
    experience = request.form.get('experience', '')
    projects = request.form.get('projects', '')
    education = request.form.get('education', '')

    prompt = f"""
    Create a professional resume summary.

    Name: {name}
    Role: {job}
    Skills: {skills}
    Experience: {experience}
    Projects: {projects}
    Education: {education}

    Keep it short, impactful (3-4 lines).
    """

    summary = call_ai(prompt)
    return jsonify({"summary": summary})

@app.route('/result')
def result():
    if 'user' not in session:
        return redirect('/login')

    data = session.get('data')
    if not data:
        return redirect('/dashboard')

    skill_list = [s.strip() for s in data['skills'].split(',') if s.strip()]
    score, missing = calculate_score(skill_list, data['job'])

    summary = data.get('summary') or generate_summary(data['name'], data['job'])

    return render_template('result.html', data=data, score=score, missing=missing, summary=summary)

@app.route('/chat', methods=['POST'])
def chat():
    user_msg = request.form.get('msg', '').strip()
    if not user_msg:
        return jsonify({"reply": "⚠️ Empty message"})

    data = session.get('data', {})
    skills = data.get('skills', '')
    role = data.get('job', '')
    name = data.get('name', '')

    skill_list = [s.strip() for s in skills.split(',') if s.strip()]
    score, missing = calculate_score(skill_list, role)

    prompt = f"""
    Candidate Name: {name}
    Role: {role}
    Skills: {skills}
    Resume Score: {score}%
    Missing Skills: {', '.join(missing) if missing else 'None'}

    Question: {user_msg}

    Give short, practical advice (3-4 lines).
    """

    reply = call_ai(prompt)
    return jsonify({"reply": reply})

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
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(data['name'], styles['Heading2']))
    story.append(Paragraph(f"{data['email']} | {data['phone']}", styles['Normal']))
    story.append(Spacer(1, 10))

    for key in ["skills", "experience", "projects", "education"]:
        if data.get(key):
            story.append(Paragraph(key.capitalize(), styles['Heading3']))
            story.append(Paragraph(data[key], styles['Normal']))
            story.append(Spacer(1, 10))

    story.append(Paragraph(f"ATS Score: {score}%", styles['Heading3']))

    doc.build(story)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name="resume.pdf",
                     mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
