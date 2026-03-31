from flask import Flask, request, redirect, session, send_file, jsonify, render_template
import os
import json
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from openai import OpenAI   # ✅ NEW IMPORT

app = Flask(__name__)
app.secret_key = "secret123"

# ✅ OPENAI CLIENT
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- DATABASE ----------
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
        json.dump(data, f)

# ---------- JOB DATABASE ----------
JOB_DATABASE = {
    "Data Scientist": ["Python", "Machine Learning", "SQL"],
    "Web Developer": ["HTML", "CSS", "JavaScript"],
    "AI Engineer": ["Python", "Deep Learning"],
    "Cloud Engineer": ["AWS", "Docker"],
    "Cybersecurity Analyst": ["Networking", "Ethical Hacking"],
    "Software Engineer": ["Java", "Python", "DSA"]
}

# ---------- OPENAI FUNCTION ----------
def call_ai(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional resume coach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )
        return response.choices[0].message.content
    except Exception as e:
        return "❌ API Error: " + str(e)

# ---------- SCORE ----------
def calculate_score(user_skills, role):
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

    if request.method == 'POST':
        data = request.form.to_dict()
        session['data'] = data

        profiles = load_json(PROFILE_FILE)
        profiles[session['user']] = data
        save_json(PROFILE_FILE, profiles)

        return redirect('/result')

    return render_template('dashboard.html')

# ✅ PROFILE PAGE
@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/login')

    profiles = load_json(PROFILE_FILE)
    user_data = profiles.get(session['user'], {})

    return render_template('profile.html', data=user_data)

# ✅ HISTORY PAGE
@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/login')

    history = load_json(HISTORY_FILE)
    user_history = history.get(session['user'], [])

    return render_template('history.html', history=user_history)

@app.route('/generate_summary', methods=['POST'])
def generate_summary():
    prompt = f"""
    Create a professional resume summary:

    Name: {request.form['name']}
    Role: {request.form['job']}
    Skills: {request.form['skills']}
    Experience: {request.form['experience']}
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

    # save history
    history = load_json(HISTORY_FILE)
    history.setdefault(session['user'], []).append(data)
    save_json(HISTORY_FILE, history)

    return render_template('result.html', data=data, score=score, missing=missing)

@app.route('/download')
def download():
    data = session.get('data')

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(data['name'], styles['Heading2']))
    story.append(Paragraph(data['skills'], styles['Normal']))

    doc.build(story)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="resume.pdf")

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
