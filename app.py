"""
TruthLens — AI Fake News Detection System
Multi-page Flask Application with Admin Authentication
"""

from flask import (
    Flask, request, jsonify, render_template,
    redirect, url_for, session, flash
)
import pickle, os, re, requests, sqlite3, numpy as np
from dotenv import load_dotenv
load_dotenv() #this opens the .env safe
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "truthlens-secret-key-change-in-production"

# ─── CONFIG ───────────────────────────────────────────────
NEWS_API_KEY = "2a2923a28707438d8fa4e52df386d9fc"
MODEL_PATH   = "model/fake_news_model.pkl"
VECTOR_PATH  = "model/tfidf_vectorizer.pkl"
DB_PATH      = "database/history.db"

# Admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USER")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# ─── LOAD MODEL ───────────────────────────────────────────
model = None
vectorizer = None

def load_model():
    global model, vectorizer
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        with open(VECTOR_PATH, "rb") as f:
            vectorizer = pickle.load(f)
        print("✅ Model loaded.")
    except FileNotFoundError:
        print("⚠️  Model not found. Run train_model.py first.")

load_model()

# ─── DATABASE ─────────────────────────────────────────────
def init_db():
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            article     TEXT,
            prediction  TEXT,
            confidence  REAL,
            word_count  INTEGER,
            timestamp   TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_to_db(article, prediction, confidence):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO analysis_history (article, prediction, confidence, word_count, timestamp) VALUES (?,?,?,?,?)",
        (article[:500], prediction, confidence, len(article.split()), datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM analysis_history")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM analysis_history WHERE prediction='REAL'")
    real = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM analysis_history WHERE prediction='FAKE'")
    fake = c.fetchone()[0]
    c.execute("SELECT AVG(confidence) FROM analysis_history")
    avg_conf = c.fetchone()[0] or 0
    c.execute("SELECT prediction, confidence, timestamp, article FROM analysis_history ORDER BY id DESC LIMIT 10")
    recent = c.fetchall()
    conn.close()
    return {
        "total": total, "real": real, "fake": fake,
        "avg_confidence": round(avg_conf, 1),
        "recent": [{"prediction": r[0], "confidence": r[1], "timestamp": r[2], "article": r[3]} for r in recent]
    }

# ─── HELPERS ──────────────────────────────────────────────
def preprocess(text):
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'[^a-z\s]', '', text)
    return re.sub(r'\s+', ' ', text).strip()

SUSPICIOUS_WORDS = [
    "shocking", "bombshell", "secret", "wake up", "sheeple", "whistleblower",
    "deep state", "mainstream media", "elites", "cover-up", "leaked", "banned",
    "censored", "suppressed", "exposed", "conspirac", "hoax", "mind control",
    "big pharma", "they don't want", "share before", "deleted"
]

def extract_keywords(text):
    return [w for w in SUSPICIOUS_WORDS if w in text.lower()][:8]

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the admin dashboard.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

def demo_news():
    return [
        {"source":"BBC News","title":"Global temperatures hit record high for third consecutive year","snippet":"Climate researchers from 42 countries published joint findings showing unprecedented warming trends across all major ocean basins.","url":"#","prediction":"REAL","confidence":94.2,"is_fake":False},
        {"source":"Reuters","title":"WHO announces new guidance on antibiotic resistance as cases rise","snippet":"The World Health Organization updated treatment protocols following a comprehensive review of resistance patterns in 80 nations.","url":"#","prediction":"REAL","confidence":91.5,"is_fake":False},
        {"source":"AP News","title":"Federal Reserve holds interest rates steady amid mixed inflation data","snippet":"The central bank's decision follows three months of data showing consumer price growth remains above the 2% target.","url":"#","prediction":"REAL","confidence":89.3,"is_fake":False},
        {"source":"Unknown Blog","title":"LEAKED: Government secretly controls weather using hidden machines!","snippet":"Anonymous source reveals cloud seeding program targeting political opponents nationwide.","url":"#","prediction":"FAKE","confidence":97.8,"is_fake":True},
        {"source":"Social Media","title":"Scientists CONFIRM 5G towers cause memory loss — study SUPPRESSED by Big Tech!","snippet":"Peer-reviewed research allegedly deleted from journals under pressure from telecom companies.","url":"#","prediction":"FAKE","confidence":98.6,"is_fake":True},
        {"source":"The Guardian","title":"Parliament passes landmark digital privacy bill protecting consumer data","snippet":"The legislation received cross-party support, introducing strict requirements for tech companies handling personal data.","url":"#","prediction":"REAL","confidence":88.1,"is_fake":False},
    ]

# ═══════════════════════════════════════════════
#  PAGE ROUTES
# ═══════════════════════════════════════════════

@app.route("/")
def home():
    return render_template("home.html", active="home")

@app.route("/analyze")
def analyze_page():
    return render_template("analyze.html", active="analyze")

@app.route("/how-it-works")
def how_it_works():
    return render_template("how_it_works.html", active="how")

@app.route("/news")
def news_page():
    return render_template("news.html", active="news")

# ─── ADMIN ────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            session["admin_user"] = username
            return redirect(url_for("admin_dashboard"))
        else:
            error = "Invalid username or password. Please try again."

    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    stats = get_stats()
    return render_template("admin_dashboard.html", stats=stats, active="admin")

# ═══════════════════════════════════════════════
#  API ROUTES
# ═══════════════════════════════════════════════

@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "No text provided"}), 400
    text = data["text"].strip()
    if len(text) < 20:
        return jsonify({"error": "Text too short."}), 400
    if model is None or vectorizer is None:
        return jsonify({"error": "Model not loaded. Run train_model.py first."}), 500

    cleaned   = preprocess(text)
    features  = vectorizer.transform([cleaned])
    prediction = model.predict(features)[0]
    score      = model.decision_function(features)[0]
    confidence = round(min(99.9, float(np.abs(score) / (np.abs(score) + 1) * 100 + 50)), 1)
    keywords   = extract_keywords(text)

    save_to_db(text, prediction, confidence)

    return jsonify({
        "prediction": prediction,
        "confidence": confidence,
        "word_count": len(text.split()),
        "keywords":   keywords,
        "is_fake":    prediction == "FAKE",
        "timestamp":  datetime.now().isoformat()
    })

@app.route("/api/news")
def api_news():
    if NEWS_API_KEY == "your_newsapi_key_here":
        return jsonify({"articles": demo_news(), "source": "demo"})
    try:
        url = (f"https://newsapi.org/v2/top-headlines?sources=bbc-news,reuters"
               f"&pageSize=6&apiKey={NEWS_API_KEY}")
        articles = requests.get(url, timeout=5).json().get("articles", [])
        results  = []
        for art in articles:
            title   = art.get("title","")
            snippet = art.get("description","") or ""
            source  = art.get("source",{}).get("name","Unknown")
            full    = f"{title}. {snippet}"
            if model and vectorizer and len(full) > 20:
                features = vectorizer.transform([preprocess(full)])
                pred     = model.predict(features)[0]
                score    = model.decision_function(features)[0]
                conf     = round(min(99.9, float(np.abs(score)/(np.abs(score)+1)*100+50)), 1)
            else:
                pred, conf = "PENDING", 0
            results.append({"source":source,"title":title,"snippet":snippet,
                            "url":art.get("url","#"),"prediction":pred,
                            "confidence":conf,"is_fake":pred=="FAKE"})
        return jsonify({"articles": results, "source": "live"})
    except Exception as e:
        return jsonify({"articles": demo_news(), "source": "demo", "error": str(e)})

@app.route("/api/stats")
@login_required
def api_stats():
    return jsonify(get_stats())

@app.route("/api/clear-history", methods=["POST" , "DELETE"])
@login_required
def clear_history():
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("DELETE FROM analysis_history")
    conn.commit(); conn.close()
    return jsonify({"message": "History cleared."})

if __name__ == "__main__":
    print(" TruthLens server starting...")
    print(" Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, host= '0.0.0.0')
