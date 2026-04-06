"""
TruthLens - Model Training Script
Run this ONCE to train and save the ML model.

Dataset: Download from Kaggle —
  https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset
  You need two files: Fake.csv and True.csv
  Place them in the 'dataset/' folder.
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import pickle
import os
import re

# ─── PATHS ────────────────────────────────────────────────
FAKE_CSV  = "dataset/Fake.csv"
TRUE_CSV  = "dataset/True.csv"
MODEL_DIR = "model"

os.makedirs(MODEL_DIR, exist_ok=True)

# ─── STEP 1: LOAD DATASET ─────────────────────────────────
print(" Loading dataset...")

try:
    fake_df = pd.read_csv(FAKE_CSV)
    true_df = pd.read_csv(TRUE_CSV)
except FileNotFoundError as e:
    print(f"\n❌ Dataset not found: {e}")
    print("\nPlease download the dataset from Kaggle:")
    print("  https://www.kaggle.com/datasets/clmentbisaillon/fake-and-real-news-dataset")
    print("\nPlace Fake.csv and True.csv in a folder called 'dataset/'")
    exit(1)

print(f"   Fake articles: {len(fake_df):,}")
print(f"   Real articles: {len(true_df):,}")

# ─── STEP 2: LABEL & COMBINE ──────────────────────────────
fake_df["label"] = "FAKE"
true_df["label"] = "REAL"
df = pd.concat([fake_df, true_df], ignore_index=True)

# Use 'text' column if it exists, otherwise combine title + text
if "text" in df.columns:
    df["content"] = df["text"].fillna("") 
else:
    df["content"] = (df.get("title", "").fillna("") + " " + df.get("text", "").fillna(""))

df = df[["content", "label"]].dropna()
df = df[df["content"].str.strip() != ""]
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle

print(f"\n✅ Total articles after cleaning: {len(df):,}")
print(f"   FAKE: {(df['label']=='FAKE').sum():,}")
print(f"   REAL: {(df['label']=='REAL').sum():,}")

# ─── STEP 3: PREPROCESS ───────────────────────────────────
def preprocess(text):
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'[^a-z\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

print("\n⚙️  Preprocessing text...")
df["content"] = df["content"].apply(preprocess)

# ─── STEP 4: SPLIT DATASET ────────────────────────────────
X = df["content"]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n Train size: {len(X_train):,} | Test size: {len(X_test):,}")

# ─── STEP 5: TF-IDF VECTORIZATION ────────────────────────
print("\n Applying TF-IDF vectorization...")
vectorizer = TfidfVectorizer(
    max_df=0.7,          # ignore terms that appear in >70% of documents
    min_df=2,            # ignore terms that appear in <2 documents
    ngram_range=(1, 2),  # unigrams + bigrams
    max_features=50000,  # top 50,000 features
    sublinear_tf=True    # apply log normalization
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf  = vectorizer.transform(X_test)

print(f"   Vocabulary size: {len(vectorizer.vocabulary_):,}")
print(f"   Feature matrix: {X_train_tfidf.shape}")

# ─── STEP 6: TRAIN MODEL ──────────────────────────────────
print("\n🤖 Training Passive Aggressive Classifier...")
model = PassiveAggressiveClassifier(
    C=0.5,               # regularization strength
    max_iter=50,
    random_state=42,
    tol=1e-3
)
model.fit(X_train_tfidf, y_train)
print("   Training complete!")

# ─── STEP 7: EVALUATE ─────────────────────────────────────
print("\n Evaluating model...")
y_pred    = model.predict(X_test_tfidf)
accuracy  = accuracy_score(y_test, y_pred)
conf_mat  = confusion_matrix(y_test, y_pred)
report    = classification_report(y_test, y_pred)

print(f"\n   ✅ Accuracy: {accuracy * 100:.2f}%")
print(f"\n   Confusion Matrix:")
print(f"   {conf_mat}")
print(f"\n   Classification Report:")
print(report)

# ─── STEP 8: SAVE MODEL ───────────────────────────────────
model_path  = os.path.join(MODEL_DIR, "fake_news_model.pkl")
vector_path = os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl")

with open(model_path, "wb") as f:
    pickle.dump(model, f)

with open(vector_path, "wb") as f:
    pickle.dump(vectorizer, f)

print(f"\n Model saved     → {model_path}")
print(f" Vectorizer saved → {vector_path}")
print(f"\n Done! Now run:  python app.py")