from flask import Flask, render_template_string, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pms.db'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---------------- USER MODEL ----------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))
    approved = db.Column(db.Boolean, default=False)

# ---------------- PROJECT MODEL ----------------
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    score = db.Column(db.Integer)
    approved = db.Column(db.Boolean, default=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# ---------------- TITLE CHECK ----------------
def evaluate_title(title):
    keywords = ['system','management','analysis','automation','prediction']
    score = sum(1 for k in keywords if k in title.lower())
    return score >= 2, score

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------------- ROUTES ----------------
@app.route('/', methods=['GET','POST'])
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
        return "Registered! Wait for Admin Approval"
    return render_template_string("""
    <h2>Register</h2>
    <form method="post">
      Name: <input name="name"><br>
      Email: <input name="email"><br>
      Password: <input type="password" name="password"><br>
      Role:
      <select name="role">
        <option>STUDENT</option>
        <option>FACULTY</option>
        <option>EXTERNAL</option>
      </select><br>
      <button>Register</button>
    </form>
    """)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email'], password=request.form['password']).first()
        if user and user.approved:
            login_user(user)
            return redirect('/dashboard')
        return "Invalid or Not Approved"
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
        users = User.query.filter_by(approved=False).all()
        projects = Project.query.order_by(Project.score.desc()).limit(10).all()
        return render_template_string("""
        <h2>Admin Dashboard</h2>
        <h3>Pending Users</h3>
        {% for u in users %}
        {{u.name}} - <a href="/approve/{{u.id}}">Approve</a><br>
        {% endfor %}
        <h3>Top 10 Projects</h3>
        {% for p in projects %}
        {{p.title}} ({{p.score}})<br>
        {% endfor %}
        """, users=users, projects=projects)

    if current_user.role == 'STUDENT':
        return render_template_string("""
        <h2>Student Dashboard</h2>
        <form method="post" action="/project">
        Project Title: <input name="title">
        <button>Submit</button>
        </form>
        """)

    return f"{current_user.role} Dashboard"

@app.route('/project', methods=['POST'])
@login_required
def project():
    ok, score = evaluate_title(request.form['title'])
    if not ok:
        return "Title NOT suitable for Final Year Project"
    p = Project(title=request.form['title'], score=score, student_id=current_user.id)
    db.session.add(p)
    db.session.commit()
    return "Title submitted, waiting for admin approval"

@app.route('/approve/<int:id>')
def approve(id):
    u = User.query.get(id)
    u.approved = True
    db.session.commit()
    return redirect('/dashboard')

# ---------------- MAIN ----------------
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='ADMIN').first():
        admin = User(
            name="ADMIN",
            email="admin@pms.com",
            password="admin",
            role="ADMIN",
            approved=True
        )
        db.session.add(admin)
        db.session.commit()

if __name__ == '__main__':
    app.run()


