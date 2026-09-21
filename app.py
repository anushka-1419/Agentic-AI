
import os
import sqlite3
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    flash
)

from werkzeug.security import generate_password_hash, check_password_hash

from hotel_agent import (
    search_hotel,
    extract_information,
    analyze_hotel,
    chat_about_hotel
)


app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "staywise-demo-secret-change-this"
)

DATABASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "staywise_users.db"
)


# ============================================================
# DATABASE
# ============================================================

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    demo_email = "demo@staywise.ai"
    demo_password = "Demo@123"

    existing_user = connection.execute(
        "SELECT id FROM users WHERE email = ?",
        (demo_email,)
    ).fetchone()

    if existing_user is None:
        connection.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
            """,
            (
                "Demo User",
                demo_email,
                generate_password_hash(demo_password)
            )
        )

    connection.commit()
    connection.close()


# ============================================================
# AUTHENTICATION HELPERS
# ============================================================

def login_required(function):
    @wraps(function)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return decorated_function


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter email and password.", "error")
            return render_template("login.html")

        connection = get_db()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(
            user["password"],
            password
        ):
            session.clear()

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            return redirect(url_for("home"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# ============================================================
# SIGNUP
# ============================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("signup.html")

        if len(password) < 6:
            flash(
                "Password must contain at least 6 characters.",
                "error"
            )
            return render_template("signup.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")

        connection = get_db()

        existing_user = connection.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:
            connection.close()
            flash(
                "An account with this email already exists.",
                "error"
            )
            return render_template("signup.html")

        hashed_password = generate_password_hash(password)

        connection.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (?, ?, ?)
            """,
            (name, email, hashed_password)
        )

        connection.commit()
        connection.close()

        flash(
            "Account created successfully. Please log in.",
            "success"
        )

        return redirect(url_for("login"))

    return render_template("signup.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")
@login_required
def home():
    return render_template(
        "index.html",
        user_name=session.get("user_name", "User")
    )


# ============================================================
# HOTEL ANALYSIS
# ============================================================

@app.route("/analyze", methods=["POST"])
@login_required
def analyze():
    try:
        data = request.get_json(silent=True) or {}

        hotel_name = str(
            data.get("hotel_name", "")
        ).strip()

        if not hotel_name:
            return jsonify({
                "success": False,
                "error": "Please enter a hotel name."
            }), 400

        search_results = search_hotel(hotel_name)

        if search_results is None:
            return jsonify({
                "success": False,
                "error": "Unable to search for hotel information."
            }), 500

        hotel_information = extract_information(
            search_results
        )

        if not hotel_information.strip():
            return jsonify({
                "success": False,
                "error": "No hotel information was found."
            }), 404

        analysis = analyze_hotel(
            hotel_name,
            hotel_information
        )

        if not analysis:
            return jsonify({
                "success": False,
                "error": (
                    "AI analysis is temporarily unavailable."
                )
            }), 503

        sources = []

        for result in search_results.get("results", []):
            sources.append({
                "title": result.get("title", "Unknown"),
                "url": result.get("url", ""),
                "content": result.get("content", "")
            })

        return jsonify({
            "success": True,
            "hotel": hotel_name,
            "analysis": analysis,
            "sources": sources
        })

    except Exception as error:
        print("ANALYZE ERROR:", repr(error))

        return jsonify({
            "success": False,
            "error": "Something went wrong during analysis."
        }), 500


# ============================================================
# CHATBOT
# ============================================================

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    try:
        data = request.get_json(silent=True) or {}

        hotel_name = str(
            data.get("hotel_name", "")
        ).strip()

        question = str(
            data.get("question", "")
        ).strip()

        analysis = str(
            data.get("analysis", "")
        )

        sources = data.get("sources", [])

        if not hotel_name or not question:
            return jsonify({
                "success": False,
                "error": "Hotel name and question are required."
            }), 400

        answer = chat_about_hotel(
            hotel_name=hotel_name,
            question=question,
            analysis=analysis,
            sources=sources
        )

        return jsonify({
            "success": True,
            "answer": answer
        })

    except Exception as error:
        print("CHAT ERROR:", repr(error))

        return jsonify({
            "success": False,
            "error": "Unable to generate chatbot response."
        }), 500


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "application": "StayWise AI"
    })


# ============================================================
# START APPLICATION
# ============================================================

init_db()

if __name__ == "__main__":
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )
