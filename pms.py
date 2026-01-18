from flask import Flask, request, redirect, url_for, render_template_string, session
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
    frontend = db.Column(db.String(200))
    backend = db.Column(db.String(200))
    documentation = db.Column(db.Text)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    description = db.Column(db.Text)

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
    <!doctype html>
    <html lang="en">
    <head>
      <title>Register</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="container mt-5">
      <h2>Register</h2>
      <form method="post" class="mb-3">
        <div class="mb-2">
          Name: <input name="name" class="form-control" required>
        </div>
        <div class="mb-2">
          Email: <input name="email" class="form-control" required>
        </div>
        <div class="mb-2">
          Password: <input type="password" name="password" class="form-control" required>
        </div>
        <div class="mb-2">
          Role:
          <select name="role" class="form-select">
            <option>STUDENT</option>
            <option>FACULTY</option>
            <option>EXTERNAL</option>
          </select>
        </div>
        <button class="btn btn-primary">Register</button>
      </form>
      <a href="/login">Already registered? Login</a>
    </body>
    </html>
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
            session['active_tab'] = None  # default tab for refresh
            return redirect('/dashboard')
        return "Invalid credentials"
    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <title>Login</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="container mt-5">
      <h2>Login</h2>
      <form method="post" class="mb-3">
        <div class="mb-2">
          Email: <input name="email" class="form-control">
        </div>
        <div class="mb-2">
          Password: <input type="password" name="password" class="form-control">
        </div>
        <button class="btn btn-primary">Login</button>
      </form>
      <a href="/">Register</a>
    </body>
    </html>
    """)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
@login_required
def dashboard():
    tab = request.args.get('tab') or session.get('active_tab') or 'home'
    session['active_tab'] = tab

    # ---------------- ADMIN ----------------
    if current_user.role == 'ADMIN':
        students = User.query.filter_by(role='STUDENT').all()
        faculty = User.query.filter_by(role='FACULTY').all()
        external = User.query.filter_by(role='EXTERNAL').all()
        projects = Project.query.filter_by(status='PENDING').all()
        top_projects = Project.query.filter_by(status='ACCEPTED').order_by(Project.score.desc()).limit(10).all()

        return render_template_string("""
        <!doctype html>
        <html lang="en">
        <head>
          <title>Admin Dashboard</title>
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container mt-3">
          <h2>Admin Dashboard</h2>
          <a href="/logout" class="btn btn-danger mb-3">Logout</a>
          <ul class="nav nav-tabs">
            <li class="nav-item">
              <a class="nav-link {% if tab=='students' %}active{% endif %}" href="{{url_for('dashboard', tab='students')}}">Students</a>
            </li>
            <li class="nav-item">
              <a class="nav-link {% if tab=='faculty' %}active{% endif %}" href="{{url_for('dashboard', tab='faculty')}}">Faculty</a>
            </li>
            <li class="nav-item">
              <a class="nav-link {% if tab=='external' %}active{% endif %}" href="{{url_for('dashboard', tab='external')}}">External</a>
            </li>
            <li class="nav-item">
              <a class="nav-link {% if tab=='projects' %}active{% endif %}" href="{{url_for('dashboard', tab='projects')}}">Pending Projects</a>
            </li>
            <li class="nav-item">
              <a class="nav-link {% if tab=='top' %}active{% endif %}" href="{{url_for('dashboard', tab='top')}}">Top Projects</a>
            </li>
          </ul>
          <div class="mt-3">
          {% if tab=='students' %}
            <h4>Students</h4>
            <table class="table table-bordered">
            <tr><th>Name</th><th>Email</th><th>Actions</th></tr>
            {% for s in students %}
              <tr>
                <td>{{s.name}}</td>
                <td>{{s.email}}</td>
                <td>
                  <a href="/edit/{{s.id}}" class="btn btn-sm btn-warning">Edit</a>
                  <a href="/delete/{{s.id}}" class="btn btn-sm btn-danger">Delete</a>
                </td>
              </tr>
            {% endfor %}
            </table>
          {% elif tab=='faculty' %}
            <h4>Faculty</h4>
            <table class="table table-bordered">
            <tr><th>Name</th><th>Email</th><th>Actions</th></tr>
            {% for f in faculty %}
              <tr>
                <td>{{f.name}}</td>
                <td>{{f.email}}</td>
                <td>
                  <a href="/edit/{{f.id}}" class="btn btn-sm btn-warning">Edit</a>
                  <a href="/delete/{{f.id}}" class="btn btn-sm btn-danger">Delete</a>
                </td>
              </tr>
            {% endfor %}
            </table>
          {% elif tab=='external' %}
            <h4>External Faculty</h4>
            <table class="table table-bordered">
            <tr><th>Name</th><th>Email</th><th>Actions</th></tr>
            {% for e in external %}
              <tr>
                <td>{{e.name}}</td>
                <td>{{e.email}}</td>
                <td>
                  <a href="/edit/{{e.id}}" class="btn btn-sm btn-warning">Edit</a>
                  <a href="/delete/{{e.id}}" class="btn btn-sm btn-danger">Delete</a>
                </td>
              </tr>
            {% endfor %}
            </table>
          {% elif tab=='projects' %}
            <h4>Pending Projects</h4>
            <table class="table table-bordered">
            <tr><th>Title</th><th>Student</th><th>Actions</th></tr>
            {% for p in projects %}
              <tr>
                <td>{{p.title}}</td>
                <td>{{p.student_id}}</td>
                <td>
                  <a href="/approve/{{p.id}}/ACCEPT" class="btn btn-sm btn-success">Accept</a>
                  <a href="/approve/{{p.id}}/REJECT" class="btn btn-sm btn-danger">Reject</a>
                </td>
              </tr>
            {% endfor %}
            </table>
          {% elif tab=='top' %}
            <h4>Top Projects</h4>
            {% for t in top_projects %}
              <p>{{t.title}} (Score: {{t.score}})</p>
            {% endfor %}
          {% endif %}
          </div>
        </body>
        </html>
        """, students=students, faculty=faculty, external=external,
           projects=projects, top_projects=top_projects, tab=tab)

    # ---------------- STUDENT ----------------
    if current_user.role == 'STUDENT':
        projects = Project.query.filter_by(student_id=current_user.id).all()
        tasks = Task.query.join(Project).filter(Project.student_id==current_user.id).all()
        return render_template_string("""
        <!doctype html>
        <html lang="en">
        <head>
          <title>Student Dashboard</title>
          <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        </head>
        <body class="container mt-3">
        <h2>Student Dashboard</h2>
        <a href="/logout" class="btn btn-danger mb-3">Logout</a>
        <ul class="nav nav-tabs mb-3">
          <li class="nav-item"><a class="nav-link {% if tab=='submit' %}active{% endif %}" href="{{url_for('dashboard', tab='submit')}}">Submit Project Title</a></li>
          <li class="nav-item"><a class="nav-link {% if tab=='details' %}active{% endif %}" href="{{url_for('dashboard', tab='details')}}">Enter Project Details</a></li>
          <li class="nav-item"><a class="nav-link {% if tab=='tasks' %}active{% endif %}" href="{{url_for('dashboard', tab='tasks')}}">Assigned Tasks</a></li>
        </ul>

        {% if tab=='submit' %}
        <form method="post" action="/project">
          <div class="mb-2">
            Project Title: <input name="title" class="form-control" required>
          </div>
          <button class="btn btn-primary">Submit</button>
        </form>
        {% elif tab=='details' %}
        {% for p in projects %}
          {% if p.status=='ACCEPTED' %}
            <form method="post" action="/project/details/{{p.id}}" class="mb-3">
              <h5>{{p.title}}</h5>
              Frontend: <input name="frontend" value="{{p.frontend or ''}}" class="form-control mb-1"><br>
              Backend: <input name="backend" value="{{p.backend or ''}}" class="form-control mb-1"><br>
              Documentation: <textarea name="documentation" class="form-control mb-1">{{p.documentation or ''}}</textarea><br>
              <button class="btn btn-success">Save Details</button>
            </form>
          {% endif %}
        {% endfor %}
        {% elif tab=='tasks' %}
        <h5>Assigned Tasks</h5>
        {% for t in tasks %}
          <p>{{t.description}}</p>
        {% endfor %}
        {% endif %}
        </body>
        </html>
        """, projects=projects, tasks=tasks, tab=tab)

    # ---------------- FACULTY / EXTERNAL ----------------
    return f"<h2>{current_user.role} Dashboard</h2><a href='/logout'>Logout</a>"

# ---------------- PROJECT ROUTES ----------------
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

@app.route('/project/details/<int:id>', methods=['POST'])
@login_required
def project_details(id):
    p = Project.query.get(id)
    if p.student_id != current_user.id:
        return "Unauthorized"
    p.frontend = request.form['frontend']
    p.backend = request.form['backend']
    p.documentation = request.form['documentation']
    db.session.commit()
    return redirect(url_for('dashboard', tab='details'))

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
    return redirect(url_for('dashboard', tab='projects'))

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
        return redirect(url_for('dashboard', tab='students'))
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
    return redirect(url_for('dashboard', tab='students'))

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
