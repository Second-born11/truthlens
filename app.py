from flask import (
    Flask, request, jsonify, render_template,
    redirect, url_for, session, flash
)
import pickle, os, re, requests, sqlite3, numpy as np
from dotenv import load_dotenv
load_dotenv() #this opens the .env safe
from datetime import datetime
from functools import wraps
import math

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# ─── CONFIG ───────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
MODEL_PATH   = "model/fake_news_model.pkl"
VECTOR_PATH  = "model/tfidf_vectorizer.pkl"
DB_PATH      = "database/history.db"
UPLOAD_FOLDER  = "uploads"
MAX_FILE_MB    = 50

ALLOWED_EXTENSIONS = {
    'mp4', 'mp3', 'wav', 'm4a',
    'pdf', 'docx', 'doc',
    'jpg', 'jpeg', 'png', 'bmp', 'tiff'
}

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_MB * 1024 * 1024
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
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
            source_type TEXT,
            timestamp   TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_to_db(article, prediction, confidence, source_type="text"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO analysis_history (article, prediction, confidence, word_count, source_type, timestamp) VALUES (?,?,?,?,?,?)",
        (article[:500], prediction, confidence, len(article.split()), source_type, datetime.now().isoformat())
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
    c.execute("SELECT prediction, confidence, timestamp, article, source_type FROM analysis_history ORDER BY id DESC LIMIT 10")
    recent = c.fetchall()
    conn.close()
    return {
        "total": total, "real": real, "fake": fake,
        "avg_confidence": round(avg_conf, 1),
        "recent": [{"prediction": r[0], "confidence": r[1], "timestamp": r[2],
                    "article": r[3], "source_type": r[4] or "text"} for r in recent]
    }

# ─── TEXT HELPERS ─────────────────────────────────────────
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

def run_model(text):
    cleaned    = preprocess(text)
    features   = vectorizer.transform([cleaned])
    prediction = model.predict(features)[0]
    score      = float(model.decision_function(features)[0])
    confidence = round(min(99.5, max(50.5, 100 / (1 + np.exp(-abs(score))))), 1)
    return prediction, confidence

# ─── FILE HELPERS ─────────────────────────────────────────
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

def extract_text_from_pdf(filepath):
    try:
        import PyPDF2
        text = ""
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        raise Exception(f"PDF reading failed: {str(e)}")

def extract_text_from_docx(filepath):
    try:
        import docx
        doc  = docx.Document(filepath)
        text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        return text.strip()
    except Exception as e:
        raise Exception(f"DOCX reading failed: {str(e)}")

def extract_text_from_image(filepath):
    try:
        import pytesseract
        from PIL import Image
        img  = Image.open(filepath)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception as e:
        raise Exception(f"Image OCR failed: {str(e)}. Make sure Tesseract is installed.")

def extract_audio_from_video(video_path, audio_path):
    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(video_path)
        clip.audio.write_audiofile(audio_path, logger=None)
        clip.close()
    except Exception as e:
        raise Exception(f"Video-to-audio conversion failed: {str(e)}")

def convert_audio_to_wav(input_path, wav_path):
    try:
        from pydub import AudioSegment
        ext   = get_extension(input_path)
        audio = AudioSegment.from_file(input_path, format=ext)
        audio.export(wav_path, format="wav")
    except Exception as e:
        raise Exception(f"Audio conversion failed: {str(e)}")

def speech_to_text(wav_path):
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        return text.strip()
    except Exception as e:
        raise Exception(f"Speech recognition failed: {str(e)}")

# ─── AUTH ─────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in to access the admin dashboard.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ─── DEMO NEWS ────────────────────────────────────────────
def demo_news():
    return [
        {"source":"BBC News","title":"Global temperatures hit record high for third consecutive year","snippet":"Climate researchers from 42 countries published joint findings showing unprecedented warming trends.","url":"#","prediction":"REAL","confidence":94.2,"is_fake":False},
        {"source":"Reuters","title":"WHO announces new guidance on antibiotic resistance as cases rise","snippet":"The World Health Organization updated treatment protocols following a comprehensive global review.","url":"#","prediction":"REAL","confidence":91.5,"is_fake":False},
        {"source":"AP News","title":"Federal Reserve holds interest rates steady amid mixed inflation data","snippet":"The central bank decision follows three months of data showing consumer price growth above target.","url":"#","prediction":"REAL","confidence":89.3,"is_fake":False},
        {"source":"Unknown Blog","title":"LEAKED: Government secretly controls weather using hidden machines!","snippet":"Anonymous source reveals cloud seeding program targeting political opponents nationwide.","url":"#","prediction":"FAKE","confidence":97.8,"is_fake":True},
        {"source":"Social Media","title":"Scientists CONFIRM 5G towers cause memory loss — study SUPPRESSED!","snippet":"Peer-reviewed research allegedly deleted from journals under pressure from telecom companies.","url":"#","prediction":"FAKE","confidence":98.6,"is_fake":True},
        {"source":"The Guardian","title":"Parliament passes landmark digital privacy bill protecting consumer data","snippet":"The legislation received cross-party support, introducing strict requirements for tech companies.","url":"#","prediction":"REAL","confidence":88.1,"is_fake":False},
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

    prediction, confidence = run_model(text)
    keywords = extract_keywords(text)
    save_to_db(text, prediction, confidence, "text")

    return jsonify({
        "prediction":  prediction,
        "confidence":  confidence,
        "word_count":  len(text.split()),
        "keywords":    keywords,
        "is_fake":     prediction == "FAKE",
        "source_type": "text",
        "timestamp":   datetime.now().isoformat()
    })

@app.route("/api/upload", methods=["POST"])
def upload_file():
    if model is None or vectorizer is None:
        return jsonify({"error": "Model not loaded. Run train_model.py first."}), 500
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "File type not supported."}), 400

    ext       = get_extension(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"upload_{timestamp}.{ext}"
    filepath  = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    extracted_text = ""
    source_type    = ext

    try:
        if ext == "pdf":
            extracted_text = extract_text_from_pdf(filepath)

        elif ext in ("docx", "doc"):
            extracted_text = extract_text_from_docx(filepath)

        elif ext in ("jpg", "jpeg", "png", "bmp", "tiff"):
            extracted_text = extract_text_from_image(filepath)

        elif ext in ("mp3", "wav", "m4a"):
            wav_path = filepath.replace(f".{ext}", "_converted.wav")
            if ext != "wav":
                convert_audio_to_wav(filepath, wav_path)
            else:
                wav_path = filepath
            extracted_text = speech_to_text(wav_path)
            if wav_path != filepath and os.path.exists(wav_path):
                os.remove(wav_path)

        elif ext == "mp4":
            audio_path = filepath.replace(".mp4", "_audio.mp3")
            wav_path   = filepath.replace(".mp4", "_audio.wav")
            extract_audio_from_video(filepath, audio_path)
            convert_audio_to_wav(audio_path, wav_path)
            extracted_text = speech_to_text(wav_path)
            for p in [audio_path, wav_path]:
                if os.path.exists(p):
                    os.remove(p)
        else:
            return jsonify({"error": "Unsupported file type."}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    if not extracted_text or len(extracted_text.strip()) < 20:
        return jsonify({
            "error": "Could not extract enough text from the file. It may be empty, corrupted, or contain no readable content."
        }), 400

    prediction, confidence = run_model(extracted_text)
    keywords = extract_keywords(extracted_text)
    save_to_db(extracted_text, prediction, confidence, source_type)

    return jsonify({
        "prediction":     prediction,
        "confidence":     confidence,
        "word_count":     len(extracted_text.split()),
        "keywords":       keywords,
        "is_fake":        prediction == "FAKE",
        "source_type":    source_type,
        "extracted_text": extracted_text[:800] + ("..." if len(extracted_text) > 800 else ""),
        "timestamp":      datetime.now().isoformat()
    })

@app.route("/api/news")
def api_news():
    if not NEWS_API_KEY:
        return jsonify({"articles": demo_news(), "source": "demo"})
    try:
        url      = (f"https://newsapi.org/v2/top-headlines?sources=bbc-news,reuters"
                    f"&pageSize=6&apiKey={NEWS_API_KEY}")
        articles = requests.get(url, timeout=5).json().get("articles", [])
        results  = []
        for art in articles:
            title   = art.get("title", "")
            snippet = art.get("description", "") or ""
            source  = art.get("source", {}).get("name", "Unknown")
            full    = f"{title}. {snippet}"
            if model and vectorizer and len(full) > 20:
                pred, conf = run_model(full)
            else:
                pred, conf = "PENDING", 0
            results.append({"source": source, "title": title, "snippet": snippet,
                            "url": art.get("url", "#"), "prediction": pred,
                            "confidence": conf, "is_fake": pred == "FAKE"})
        return jsonify({"articles": results, "source": "live"})
    except Exception as e:
        return jsonify({"articles": demo_news(), "source": "demo", "error": str(e)})

@app.route("/api/stats")
@login_required
def api_stats():
    return jsonify(get_stats())

@app.route("/api/clear-history", methods=["POST", "DELETE"])
@login_required
def clear_history():
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().execute("DELETE FROM analysis_history")
    conn.commit()
    conn.close()
    return jsonify({"message": "History cleared."})

if __name__ == "__main__":
    print(" TruthLens server starting...")
    print(" Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, host= '0.0.0.0')
