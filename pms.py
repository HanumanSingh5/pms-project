from flask import Flask, request, redirect, url_for, render_template, session
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

# ---------------- Models ----------------
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

# ---------------- Utils ----------------
def evaluate_title(title):
    title = title.strip().lower()
    keywords = [
        'system', 'management', 'application', 'portal', 'app',
        'online', 'attendance', 'library', 'student',
        'college', 'project', 'automation'
    ]
    score = 0
    if len(title.split()) < 3 or len(title) < 15:
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

# ---------------- Routes ----------------
@app.route('/', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        if not is_gmail(email):
            return "? Only official Gmail allowed"
        user = User(
            name=request.form['name'].upper(),
            email=email,
            password=request.form['password'],
            role=request.form['role']
        )
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'], password=request.form['password']).first()
        if user:
            login_user(user)
            session['active_tab'] = None
            return redirect(url_for('dashboard'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

@app.route('/dashboard')
@login_required
def dashboard():
    tab = request.args.get('tab') or session.get('active_tab') or 'home'
    session['active_tab'] = tab

    if current_user.role == 'ADMIN':
        students = User.query.filter_by(role='STUDENT').all()
        faculty = User.query.filter_by(role='FACULTY').all()
        external = User.query.filter_by(role='EXTERNAL').all()
        projects = Project.query.filter_by(status='PENDING').all()
        top_projects = Project.query.filter_by(status='ACCEPTED').order_by(Project.score.desc()).limit(10).all()
        return render_template('dashboard_admin.html', tab=tab, students=students, faculty=faculty,
                               external=external, projects=projects, top_projects=top_projects)

    if current_user.role == 'STUDENT':
        projects = Project.query.filter_by(student_id=current_user.id).all()
        tasks = Task.query.join(Project).filter(Project.student_id==current_user.id).all()
        return render_template('dashboard_student.html', tab=tab, projects=projects, tasks=tasks)

    if current_user.role == 'FACULTY':
        projects = Project.query.filter_by(status='ACCEPTED').all()
        return render_template('dashboard_faculty.html', tab=tab, projects=projects)

    if current_user.role == 'EXTERNAL':
        projects = Project.query.filter_by(status='ACCEPTED').all()
        return render_template('dashboard_external.html', projects=projects)

# ---------------- Project Routes ----------------
@app.route('/project', methods=['POST'])
@login_required
def project():
    ok, score = evaluate_title(request.form['title'])
    if not ok:
        return "? Title not suitable for Final Year Project"
    p = Project(title=request.form['title'], score=score, student_id=current_user.id)
    db.session.add(p)
    db.session.commit()
    return "? Title submitted."

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
    project.status = 'ACCEPTED' if action.upper()=='ACCEPT' else 'REJECTED'
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
        admin = User(name='ADMIN', email='admin@pms.com', password='admin', role='ADMIN')
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
