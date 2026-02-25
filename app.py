import os
import psycopg2
from flask import Flask, render_template, request, redirect, session
from werkzeug.utils import secure_filename

# ---------------- APP SETUP ----------------

app = Flask(__name__)
app.secret_key = "justicecloud_final_project_key"

# ---------------- DATABASE ----------------

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db_connection():
    if not DATABASE_URL:
        raise Exception("DATABASE_URL not found in environment variables")

    return psycopg2.connect(
        DATABASE_URL,
        sslmode="require"
    )

# ---------------- INIT DATABASE ----------------

def init_db():
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # Create users table
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE,
            password VARCHAR(100),
            role VARCHAR(50)
        )
        """)

        # Create cases table
        c.execute("""
        CREATE TABLE IF NOT EXISTS cases(
            id SERIAL PRIMARY KEY,
            case_number VARCHAR(100),
            client_name VARCHAR(100),
            case_type VARCHAR(100),
            hearing_date VARCHAR(100),
            status VARCHAR(50),
            document VARCHAR(200)
        )
        """)

        # Ensure admin exists
        c.execute("SELECT * FROM users WHERE username=%s", ("admin",))
        admin = c.fetchone()

        if not admin:
            c.execute("""
            INSERT INTO users(username,password,role)
            VALUES(%s,%s,%s)
            """, ("admin","admin123","Administrator"))

        conn.commit()
        conn.close()

    except Exception as e:
        print("DB INIT ERROR:", e)

# 🔥 IMPORTANT: FORCE DB INIT ON STARTUP (FOR GUNICORN)
init_db()

# ---------------- FILE UPLOAD ----------------

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    return redirect("/login")

# ---------- LOGIN ----------

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        try:
            conn = get_db_connection()
            c = conn.cursor()

            c.execute("""
            SELECT * FROM users
            WHERE username=%s AND password=%s
            """,(username,password))

            user = c.fetchone()
            conn.close()

            if user:
                session["user"] = user[1]
                session["role"] = user[3]
                return redirect("/dashboard")

        except Exception as e:
            print("Login error:", e)

    return render_template("login.html")

# ---------- DASHBOARD ----------

@app.route("/dashboard")
def dashboard():

    if "user" not in session:
        return redirect("/login")

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM cases")
    total_cases = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM cases WHERE status='Open'")
    open_cases = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM cases WHERE status='Closed'")
    closed_cases = c.fetchone()[0]

    conn.close()

    prediction = 0
    if total_cases > 0:
        prediction = round((closed_cases / total_cases) * 100,2)

    return render_template(
        "dashboard.html",
        user=session["user"],
        role=session["role"],
        total=total_cases,
        open_cases=open_cases,
        closed_cases=closed_cases,
        prediction=prediction
    )

# ---------- ADD CASE ----------

@app.route("/add_case", methods=["GET","POST"])
def add_case():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        case_number = request.form.get("case_number")
        client_name = request.form.get("client_name")
        case_type = request.form.get("case_type")
        hearing_date = request.form.get("hearing_date")
        status = request.form.get("status")

        document = ""

        if "file" in request.files:
            file = request.files["file"]
            if file.filename != "":
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                document = filename

        conn = get_db_connection()
        c = conn.cursor()

        c.execute("""
        INSERT INTO cases
        (case_number,client_name,case_type,hearing_date,status,document)
        VALUES(%s,%s,%s,%s,%s,%s)
        """,(case_number,client_name,case_type,hearing_date,status,document))

        conn.commit()
        conn.close()

        return redirect("/dashboard")

    return render_template("add_case.html")

# ---------- VIEW CASES ----------

@app.route("/view_cases")
def view_cases():

    if "user" not in session:
        return redirect("/login")

    search = request.args.get("search")

    conn = get_db_connection()
    c = conn.cursor()

    if search:
        c.execute("SELECT * FROM cases WHERE case_number LIKE %s",
                  ("%"+search+"%",))
    else:
        c.execute("SELECT * FROM cases")

    cases = c.fetchall()
    conn.close()

    return render_template("view_cases.html", cases=cases)

# ---------- LOGOUT ----------

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN (LOCAL ONLY) ----------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)