from flask import Flask, request, render_template_string, send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
styles = getSampleStyleSheet()

# ✅ Expanded Job Database
JOB_DATABASE = {
    "Data Scientist": ["Python", "Machine Learning", "SQL", "Statistics", "Data Analysis"],
    "Web Developer": ["HTML", "CSS", "JavaScript", "React", "API"],
    "AI Engineer": ["Python", "Deep Learning", "Neural Networks", "TensorFlow"],
    "Software Engineer": ["Python", "Java", "Data Structures", "Algorithms", "Git"],
    "Data Analyst": ["Excel", "SQL", "Python", "Data Visualization", "Statistics"]
}

# ✅ Skill Descriptions Generator
def generate_skill_descriptions(skills):
    descriptions = []
    for skill in skills:
        descriptions.append(f"{skill}: Demonstrated practical knowledge and applied experience.")
    return descriptions

# ✅ NLP Resume Summary
def generate_summary(name, role):
    return f"{name} is an aspiring {role} with strong technical proficiency and problem-solving capabilities."

# ✅ ATS Score Logic (FIXED VERSION ONLY)
def calculate_score(user_skills, role):
    required_skills = JOB_DATABASE.get(role, [])

    # Clean and normalize skills
    user_skills_clean = [skill.strip().lower() for skill in user_skills]
    required_skills_clean = [skill.strip().lower() for skill in required_skills]

    matched = len(set(user_skills_clean).intersection(required_skills_clean))

    score = (matched / len(required_skills_clean)) * 100 if required_skills_clean else 0

    # Keep original formatting for missing skills
    missing_skills = [
        skill for skill in required_skills
        if skill.lower() not in user_skills_clean
    ]

    return round(score, 2), missing_skills

# ✅ Professional PDF Generator
def generate_pdf(name, email, phone, summary, skills, education, certifications):
    filename = f"{name}_Resume.pdf"

    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []

    elements.append(Paragraph(f"<b>{name}</b>", styles['Title']))
    elements.append(Paragraph(f"{email} | {phone}", styles['BodyText']))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("<b>Professional Summary</b>", styles['Heading2']))
    elements.append(Paragraph(summary, styles['BodyText']))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>Skills</b>", styles['Heading2']))
    for skill in skills:
        elements.append(Paragraph(f"• {skill}", styles['BodyText']))

    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>Education</b>", styles['Heading2']))
    elements.append(Paragraph(education, styles['BodyText']))

    if certifications:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<b>Certifications</b>", styles['Heading2']))
        elements.append(Paragraph(certifications, styles['BodyText']))

    doc.build(elements)

    return filename

# ✅ WEBSITE UI (UNCHANGED)
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Resume Analyzer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f5f7fa;
            padding: 40px;
        }
        .container {
            background: white;
            padding: 30px;
            max-width: 750px;
            margin: auto;
            border-radius: 10px;
            box-shadow: 0px 5px 15px rgba(0,0,0,0.1);
        }
        h2 {
            text-align: center;
        }
        input, select {
            width: 100%;
            padding: 10px;
            margin-bottom: 12px;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #3498db;
            color: white;
            border: none;
        }
        .result {
            margin-top: 20px;
            background: #ecf0f1;
            padding: 15px;
        }
        .progress {
            background: #ddd;
            border-radius: 20px;
            overflow: hidden;
            height: 25px;
            margin-top: 10px;
        }
        .progress-bar {
            height: 100%;
            background: #27ae60;
            text-align: center;
            color: white;
            line-height: 25px;
        }
        .download-btn {
            background: #27ae60;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>AI Resume Builder & ATS Analyzer</h2>

        <form method="post">

            <label>Name</label>
            <input type="text" name="name" required>

            <label>Email</label>
            <input type="email" name="email" required>

            <label>Phone</label>
            <input type="text" name="phone" required>

            <label>Skills (comma separated)</label>
            <input type="text" name="skills" required>

            <label>Qualification</label>
            <select name="education">
                <option>BTech</option>
                <option>MTech</option>
                <option>MBA</option>
                <option>BSc</option>
                <option>MSc</option>
                <option>BCA</option>
                <option>MCA</option>
            </select>

            <label>Certifications</label>
            <input type="text" name="certifications">

            <label>Target Role</label>
            <select name="role">
                <option>Data Scientist</option>
                <option>Web Developer</option>
                <option>AI Engineer</option>
                <option>Software Engineer</option>
                <option>Data Analyst</option>
            </select>

            <button type="submit">Analyze Resume</button>
        </form>

        {% if result %}
        <div class="result">
            <p><b>Summary:</b> {{ result.summary }}</p>

            <p><b>ATS Score:</b></p>
            <div class="progress">
                <div class="progress-bar" style="width: {{ result.score }}%">
                    {{ result.score }}%
                </div>
            </div>

            <p><b>Missing Skills:</b> {{ result.missing }}</p>

            <p><b>Skill Descriptions:</b></p>
            {{ result.skill_desc | safe }}

            <form action="/download/{{ result.pdf }}">
                <button class="download-btn">Download Resume PDF</button>
            </form>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    result = None

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        skills = request.form['skills'].split(',')
        skills = [s.strip() for s in skills]
        education = request.form['education']
        certifications = request.form['certifications']
        role = request.form['role']

        summary = generate_summary(name, role)

        score, missing_skills = calculate_score(skills, role)

        skill_descriptions = generate_skill_descriptions(skills)
        skill_desc_html = "<br>".join(skill_descriptions)

        pdf_file = generate_pdf(name, email, phone, summary, skills, education, certifications)

        result = {
            "summary": summary,
            "score": score,
            "missing": ", ".join(missing_skills),
            "skill_desc": skill_desc_html,
            "pdf": pdf_file
        }

    return render_template_string(HTML_PAGE, result=result)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)