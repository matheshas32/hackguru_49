"""
Train the event post classifier.

Approach: a stacked model that combines:
  1) TF-IDF over the textual content  -> learns scam keyword/phrase patterns
  2) Hand-crafted numeric features   -> source credibility & structural signals

We blend a LinearSVC/LogisticRegression on the text + a RandomForest on the
hand-crafted features, then calibrate probabilities.
"""
from __future__ import annotations

import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
                             f1_score, roc_auc_score)
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import make_pipeline

from .features import FEATURE_NAMES, extract_features

MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
MODEL_DIR.mkdir(exist_ok=True)


class EventScannerModel:
    def __init__(self):
        self.tfidf = TfidfVectorizer(
            lowercase=True, stop_words="english", max_features=8000,
            ngram_range=(1, 2), min_df=2,
        )
        # Text classifier (calibrated so .predict_proba is meaningful)
        self.text_clf = CalibratedClassifierCV(
            LogisticRegression(max_iter=3000, C=2.0), cv=3
        )
        # Structural / hand-crafted feature classifier
        self.struct_clf = RandomForestClassifier(
            n_estimators=300, max_depth=12, min_samples_leaf=2,
            random_state=42, n_jobs=-1,
        )
        # Blend weights
        self.w_text = 0.6
        self.w_struct = 0.4

    def fit(self, posts, labels):
        texts = [p.full_text for p in posts]
        X_text = self.tfidf.fit_transform(texts)
        X_struct = np.array([extract_features(p) for p in posts])

        self.text_clf.fit(X_text, labels)
        self.struct_clf.fit(X_struct, labels)
        return self

    def predict_proba(self, posts):
        """Return P(FAKE) per post, blended from both classifiers."""
        texts = [p.full_text for p in posts]
        X_text = self.tfidf.transform(texts)
        X_struct = np.array([extract_features(p) for p in posts])

        p_text = self.text_clf.predict_proba(X_text)[:, 1]      # P(fake)
        p_struct = self.struct_clf.predict_proba(X_struct)[:, 1]
        return self.w_text * p_text + self.w_struct * p_struct

    def predict(self, posts):
        return (self.predict_proba(posts) >= 0.5).astype(int)

    def save(self, path: str | os.PathLike | None = None):
        path = Path(path) if path else MODEL_DIR / "event_scanner_model.joblib"
        joblib.dump(self, path)
        return path

    @classmethod
    def load(cls, path: str | os.PathLike | None = None):
        path = Path(path) if path else MODEL_DIR / "event_scanner_model.joblib"
        return joblib.load(path)


def train(posts, labels, test_size=0.2, seed=42):
    """Train, evaluate, and report cross-validated metrics."""
    Xtr, Xte, ytr, yte = train_test_split(
        posts, labels, test_size=test_size, random_state=seed, stratify=labels
    )
    model = EventScannerModel()
    model.fit(Xtr, ytr)

    # Cross-validation estimate of the blended text model
    cv = cross_val_score(
        make_pipeline(
            TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2), min_df=2),
            LogisticRegression(max_iter=3000, C=2.0),
        ),
        [p.full_text for p in Xtr], ytr, cv=5, scoring="f1",
    )

    probs = model.predict_proba(Xte)
    preds = (probs >= 0.5).astype(int)

    print("=" * 64)
    print("EVENT POST CLASSIFIER  —  train/evaluate")
    print("=" * 64)
    print(f"Train/Test split: {len(Xtr)} / {len(Xte)}  (test={test_size:.0%})")
    print(f"Blend: text 60% + structural 40%")
    print(f"5-fold CV F1 (text head): {cv.mean():.3f} ± {cv.std():.3f}")
    print("-" * 64)
    print(f"Accuracy : {accuracy_score(yte, preds):.3f}")
    print(f"F1  (FAKE) : {f1_score(yte, preds):.3f}")
    print(f"AUC  (FAKE): {roc_auc_score(yte, probs):.3f}")
    print("-" * 64)
    print(classification_report(yte, preds, target_names=["REAL", "FAKE"]))
    print("=" * 64)

    # Feature importances from the structural RF
    imp = model.struct_clf.feature_importances_
    order = np.argsort(imp)[::-1][:12]
    print("\nTop structural signals learned by the model:")
    for i in order:
        print(f"  {FEATURE_NAMES[i]:<22} {imp[i]:.3f}")
    return model
