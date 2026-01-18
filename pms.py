from flask import Flask, request, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import re

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
    status = db.Column(db.String(20), default="PENDING")  # PENDING / ACCEPTED / REJECTED
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ---------------- UTILS ----------------
def evaluate_title(title):
    title = title.strip().lower()
    keywords = [
        'system', 'management', 'application', 'portal', 'app',
        'online', 'attendance', 'library', 'student',
        'college', 'project', 'automation'
    ]
    score = 0
    if len(title.split()) < 3:
        return False, 0
    if len(title) < 15:
        return False, 0
    for k in keywords:
        if k in title:
            score += 1
    return score >= 1, score

def is_gmail(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@gmail\.com$', email)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- ROUTES ----------------
@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        if not is_gmail(email):
            return "❌ Only official Gmail allowed"
        user = User(
            name=request.form['name'].upper(),
            email=email,
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

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'ADMIN':
        students = User.query.filter_by(role='STUDENT').all()
        faculty = User.query.filter_by(role='FACULTY').all()
        external = User.query.filter_by(role='EXTERNAL').all()
        projects = Project.query.filter_by(status='PENDING').all()
        top_projects = Project.query.filter_by(status='ACCEPTED').order_by(Project.score.desc()).limit(10).all()

        return render_template_string("""
        <h2>Admin Dashboard</h2>
        <a href="/logout">Logout</a>
        <hr>

        <h3>Students</h3>
        {% for s in students %}
            {{s.name}} ({{s.email}})
            <a href="/edit/{{s.id}}">Edit</a>
            <a href="/delete/{{s.id}}">Delete</a><br>
        {% endfor %}

        <h3>Faculties</h3>
        {% for f in faculty %}
            {{f.name}} ({{f.email}})
            <a href="/edit/{{f.id}}">Edit</a>
            <a href="/delete/{{f.id}}">Delete</a><br>
        {% endfor %}

        <h3>External Faculties</h3>
        {% for e in external %}
            {{e.name}} ({{e.email}})
            <a href="/edit/{{e.id}}">Edit</a>
            <a href="/delete/{{e.id}}">Delete</a><br>
        {% endfor %}

        <h3>Project Titles Pending Approval</h3>
        {% for p in projects %}
            {{p.title}} by {{p.student_id}}
            <a href="/approve/{{p.id}}/accept">Accept</a>
            <a href="/approve/{{p.id}}/reject">Reject</a><br>
        {% endfor %}

        <h3>Top Projects</h3>
        {% for t in top_projects %}
            {{t.title}} (Score: {{t.score}})<br>
        {% endfor %}
        """ , students=students, faculty=faculty, external=external, projects=projects, top_projects=top_projects)

    if current_user.role == 'STUDENT':
        return render_template_string("""
        <h2>Student Dashboard</h2>
        <a href="/logout">Logout</a><br><br>
        <form method="post" action="/project">
          Project Title: <input name="title" required>
          <button>Submit</button>
        </form>
        """)

    return f"<h2>{current_user.role} Dashboard</h2><a href='/logout'>Logout</a>"

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

@app.route('/approve/<int:id>/<action>')
@login_required
def approve(id, action):
    if current_user.role != 'ADMIN':
        return "Unauthorized"
    project = Project.query.get(id)
    if action.upper() == 'ACCEPT':
        project.status = 'ACCEPTED'
    else:
        project.status = 'REJECTED'
    db.session.commit()
    return redirect('/dashboard')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    if current_user.role != 'ADMIN':
        return "Unauthorized"
    user = User.query.get(id)
    if request.method == 'POST':
        user.name = request.form['name'].upper()
        user.email = request.form['email']
        user.password = request.form['password']
        db.session.commit()
        return redirect('/dashboard')
    return render_template_string("""
    <h2>Edit User</h2>
    <form method="post">
      Name: <input name="name" value="{{user.name}}" required><br>
      Email: <input name="email" value="{{user.email}}" required><br>
      Password: <input name="password" value="{{user.password}}" required><br>
      <button>Update</button>
    </form>
    """, user=user)

@app.route('/delete/<int:id>')
@login_required
def delete_user(id):
    if current_user.role != 'ADMIN':
        return "Unauthorized"
    user = User.query.get(id)
    db.session.delete(user)
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





