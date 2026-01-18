from flask import Flask, request, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------------- MODELS ----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))  # STUDENT, FACULTY, EXTERNAL, ADMIN

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    score = db.Column(db.Integer)
    approved = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ---------------- UTILS ----------------

def evaluate_title(title):
    keywords = ['system', 'management', 'analysis', 'automation', 'prediction']
    score = sum(1 for k in keywords if k in title.lower())
    if len(title.split()) < 4:
        return False, score
    return score >= 2, score

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- ROUTES ----------------

@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(
            name=request.form['name'].upper(),
            email=request.form['email'],
            password=request.form['password'],
            role=request.form['role']
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template_string("""
    <h2>Register</h2>
    <form method="post">
      Name: <input name="name" required><br>
      Email: <input name="email" required><br>
      Password: <input type="password" name="password" required><br>
      Role:
      <select name="role">
        <option>STUDENT</option>
        <option>FACULTY</option>
        <option>EXTERNAL</option>
      </select><br><br>
      <button>Register</button>
    </form>
    <a href="/login">Already registered? Login</a>
    """)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(
            email=request.form['email'],
            password=request.form['password']
        ).first()
        if user:
            login_user(user)
            return redirect('/dashboard')
        return "Invalid credentials"

    return render_template_string("""
    <h2>Login</h2>
    <form method="post">
      Email: <input name="email"><br>
      Password: <input type="password" name="password"><br>
      <button>Login</button>
    </form>
    """)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'ADMIN':
        students = User.query.filter_by(role='STUDENT').all()
        faculty = User.query.filter_by(role='FACULTY').all()
        external = User.query.filter_by(role='EXTERNAL').all()
        projects = Project.query.all()
        top_projects = Project.query.filter_by(approved=True).order_by(Project.score.desc()).limit(10).all()

        return render_template_string("""
        <h2>Admin Dashboard</h2>

        <h3>Students</h3>
        {% for s in students %} {{s.name}} ({{s.email}})<br> {% endfor %}

        <h3>Faculties</h3>
        {% for f in faculty %} {{f.name}} ({{f.email}})<br> {% endfor %}

        <h3>External Faculties</h3>
        {% for e in external %} {{e.name}} ({{e.email}})<br> {% endfor %}

        <h3>Projects (Approve Titles)</h3>
        {% for p in projects %}
          {{p.title}} - Score: {{p.score}}
          {% if not p.approved %}
            <a href="/approve/{{p.id}}">Approve</a>
          {% endif %}
          <br>
        {% endfor %}

        <h3>Top Projects</h3>
        {% for t in top_projects %}
          {{t.title}} ({{t.score}})<br>
        {% endfor %}
        """)

    if current_user.role == 'STUDENT':
        return render_template_string("""
        <h2>Student Dashboard</h2>
        <form method="post" action="/project">
          Project Title: <input name="title">
          <button>Submit</button>
        </form>
        """)

    return f"<h2>{current_user.role} Dashboard</h2>"

@app.route('/project', methods=['POST'])
@login_required
def project():
    ok, score = evaluate_title(request.form['title'])
    if not ok:
        return "❌ Title not suitable for Final Year Project"

    p = Project(
        title=request.form['title'],
        score=score,
        student_id=current_user.id
    )
    db.session.add(p)
    db.session.commit()
    return "✅ Title submitted. Waiting for admin approval."

@app.route('/approve/<int:id>')
@login_required
def approve(id):
    if current_user.role != 'ADMIN':
        return "Unauthorized"
    project = Project.query.get(id)
    project.approved = True
    db.session.commit()
    return redirect('/dashboard')

# ---------------- INIT ----------------

with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='ADMIN').first():
        admin = User(
            name='ADMIN',
            email='admin@pms.com',
            password='admin',
            role='ADMIN'
        )
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run()



