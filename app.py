from flask import Flask, render_template, request, redirect, url_for, session
from supabase import create_client
import bcrypt, re

app = Flask(__name__)
app.secret_key = "Retrix"

# ---------------- SUPABASE ----------------
SUPABASE_URL = "https://floxzvupabedgopcpkbs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZsb3h6dnVwYWJlZGdvcGNwa2JzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc0NjEwODAsImV4cCI6MjA4MzAzNzA4MH0.g3FDqmraLlRFnMMJcCSLCEtjY6wIH_OPauLCXYN8mw8"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- PASSWORD VALIDATION ----------------
def valid_password(pwd):
    return (
        len(pwd) >= 8 and
        re.search(r"[A-Z]", pwd) and
        re.search(r"[a-z]", pwd) and
        re.search(r"\d", pwd) and
        re.search(r"[!@#$%^&*]", pwd)
    )

# ---------------- SPLASH ----------------
@app.route("/")
def index():
    return render_template("index.html")

# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not valid_password(password):
            return render_template("signup.html", error="Password too weak")

        # Check email
        if supabase.table("users").select("id").eq("email", email).execute().data:
            return render_template("signup.html", error="Email already registered")

        # Check username
        if supabase.table("users").select("id").eq("username", username).execute().data:
            return render_template("signup.html", error="Username already taken")

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        supabase.table("users").insert({
            "username": username,
            "email": email,
            "password": hashed
        }).execute()

        return redirect(url_for("login"))

    return render_template("signup.html")

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["identifier"].strip().lower()
        password = request.form["password"]

        # Try email
        res = supabase.table("users").select("*").eq("email", identifier).execute()

        # Try username
        if not res.data:
            res = supabase.table("users").select("*").eq("username", identifier).execute()

        if not res.data:
            return render_template("login.html", error="User not found")

        user = res.data[0]

        if not bcrypt.checkpw(password.encode(), user["password"].encode()):
            return render_template("login.html", error="Incorrect password")

        session["user"] = user["username"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"])

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- FORGOT / RESET ----------------
@app.route("/forgot-password")
def forgot_password():
    return render_template("forget_password.html")

@app.route("/reset-password")
def reset_password():
    return render_template("reset_password.html")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
