from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "elitejusticecloudsystem"

# ---------------- FILE UPLOAD ----------------

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- DATABASE CORE ----------------

def init_db():
    
    conn = sqlite3.connect("justice.db")
    c = conn.cursor()

def get_db_connection():
    conn = sqlite3.connect("justice.db")
    conn.row_factory = sqlite3.Row
    return conn

def admin_required(f):
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect("/login")

        if session.get("role") != "Administrator":
            return redirect("/dashboard")

        return f(*args, **kwargs)

    wrapper.__name__ = f.__name__
    return wrapper
    
    # Users table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    # Cases table
    c.execute("""
    CREATE TABLE IF NOT EXISTS cases(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_number TEXT,
        client_name TEXT,
        case_type TEXT,
        hearing_date TEXT,
        status TEXT,
        document TEXT
    )
    """)

    # Default accounts
    c.execute("INSERT OR IGNORE INTO users(id,username,password,role) VALUES(1,'admin','admin123','Administrator')")
    c.execute("INSERT OR IGNORE INTO users(id,username,password,role) VALUES(2,'clerk','clerk123','Clerk')")

    conn.commit()
    conn.close()

init_db()

# ---------------- AI STYLE PREDICTION ENGINE ----------------

def prediction_engine(total, closed):

    if total == 0:
        return 0

    # Simulation model (academic AI demo)
    return int((closed / total) * 100)

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return redirect("/login")

# ---------- LOGIN ----------

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("justice.db")
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (username,password))

        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            session["role"] = user[3]

            return redirect("/dashboard")

    return render_template("login.html")

# ---------- DASHBOARD ----------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("justice.db")
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM cases")
    total_cases = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM cases WHERE status='Open'")
    open_cases = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM cases WHERE status='Closed'")
    closed_cases = c.fetchone()[0]

    conn.close()

    prediction = prediction_engine(total_cases, closed_cases)

    return render_template("dashboard.html",
                           user=session["user"],
                           role=session["role"],
                           total=total_cases,
                           open_cases=open_cases,
                           closed_cases=closed_cases,
                           prediction=prediction)

# ---------- ADD CASE ----------

@app.route("/add_case", methods=["GET","POST"])
def add_case():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        case_number = request.form["case_number"]
        client_name = request.form["client_name"]
        case_type = request.form["case_type"]
        hearing_date = request.form["hearing_date"]
        status = request.form["status"]

        document = ""

        if "file" in request.files:

            file = request.files["file"]

            if file.filename != "":
                filename = secure_filename(file.filename)

                file.save(os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                ))

                document = filename

        conn = sqlite3.connect("justice.db")
        c = conn.cursor()

        c.execute("""
        INSERT INTO cases(case_number,client_name,case_type,hearing_date,status,document)
        VALUES(?,?,?,?,?,?)
        """,(case_number,client_name,case_type,hearing_date,status,document))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_case.html")

# ---------- VIEW + SEARCH CASES ----------

@app.route("/view_cases")
def view_cases():

    if "user" not in session:
        return redirect("/login")

    search = request.args.get("search")

    conn = sqlite3.connect("justice.db")
    c = conn.cursor()

    if search:
        c.execute("SELECT * FROM cases WHERE case_number LIKE ?",
                  ("%"+search+"%",))
    else:
        c.execute("SELECT * FROM cases")

    cases = c.fetchall()
    conn.close()

    return render_template("view_cases.html", cases=cases)

# ---------- REPORT DOWNLOAD ----------

@app.route("/report")
def report():
    return redirect("/static/court_report.pdf")

# ---------- LOGOUT ----------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(debug=True)