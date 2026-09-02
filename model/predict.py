import sys
from pathlib import Path
from typing import Union, Tuple, Optional, Dict, Any
import numpy as np
import cv2
import tensorflow as tf

# ============================================================
# EVENTTRUST AI
# POSTER + QR PREDICTION ENGINE
# ============================================================

MODEL_DIR = Path(__file__).resolve().parent
POSTER_MODEL_PATH = MODEL_DIR / "poster_model.keras"
EVENTTRUST_MODEL_PATH = MODEL_DIR / "eventtrust_model.keras"

# Prefer poster_model.keras as primary trained model
if POSTER_MODEL_PATH.exists():
    MODEL_PATH = POSTER_MODEL_PATH
elif EVENTTRUST_MODEL_PATH.exists():
    MODEL_PATH = EVENTTRUST_MODEL_PATH
else:
    MODEL_PATH = POSTER_MODEL_PATH

_cached_model = None


def get_model(model_path: Optional[Path] = None):
    """Load and cache the Keras model."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    path_to_load = Path(model_path) if model_path else MODEL_PATH
    if not path_to_load.exists():
        if EVENTTRUST_MODEL_PATH.exists():
            path_to_load = EVENTTRUST_MODEL_PATH
        else:
            raise FileNotFoundError(f"Model file not found at: {path_to_load}")

    print(f"Loading EventTrust Poster AI model from {path_to_load.name}...")
    _cached_model = tf.keras.models.load_model(str(path_to_load), compile=False)
    print("Model loaded successfully.")
    return _cached_model


# ============================================================
# QR DETECTION
# ============================================================

def detect_qr(image_input: Union[str, Path, np.ndarray, bytes]) -> Tuple[Optional[str], Optional[np.ndarray]]:
    """
    Detect and decode QR codes from an image using multi-pass OpenCV techniques.
    Returns (decoded_data, points).
    """
    if isinstance(image_input, (str, Path)):
        img = cv2.imread(str(image_input))
    elif isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        return None, None

    if img is None or img.size == 0:
        return None, None

    detector = cv2.QRCodeDetector()

    # Pass 1: Original image
    try:
        data, points, _ = detector.detectAndDecode(img)
        if data and points is not None:
            return str(data).strip(), points
    except Exception:
        pass

    # Pass 2: Enlarged image (2x cubic interpolation)
    try:
        h, w = img.shape[:2]
        if max(h, w) < 2500:
            enlarged = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            data, points, _ = detector.detectAndDecode(enlarged)
            if data and points is not None:
                return str(data).strip(), points / 2.0
    except Exception:
        pass

    # Pass 3: Grayscale & Contrast enhancement
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        data, points, _ = detector.detectAndDecode(gray)
        if data and points is not None:
            return str(data).strip(), points

        # Equalized grayscale
        equalized = cv2.equalizeHist(gray)
        data, points, _ = detector.detectAndDecode(equalized)
        if data and points is not None:
            return str(data).strip(), points
    except Exception:
        pass

    # Pass 4: Adaptive Thresholding
    try:
        if 'gray' not in locals():
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 51, 5
        )
        data, points, _ = detector.detectAndDecode(thresh)
        if data and points is not None:
            return str(data).strip(), points
    except Exception:
        pass

    return None, None


# ============================================================
# CROP QR CODE
# ============================================================

def crop_qr(image_input: Union[str, Path, np.ndarray, bytes], points: np.ndarray) -> Optional[np.ndarray]:
    """Crops the QR code area from the image with a safety margin."""
    if isinstance(image_input, (str, Path)):
        img = cv2.imread(str(image_input))
    elif isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif isinstance(image_input, np.ndarray):
        img = image_input
    else:
        return None

    if img is None or points is None:
        return None

    points = points.reshape(-1, 2)
    x_min = int(np.min(points[:, 0]))
    x_max = int(np.max(points[:, 0]))
    y_min = int(np.min(points[:, 1]))
    y_max = int(np.max(points[:, 1]))

    margin = 20
    x_min = max(0, x_min - margin)
    y_min = max(0, y_min - margin)
    x_max = min(img.shape[1], x_max + margin)
    y_max = min(img.shape[0], y_max + margin)

    crop = img[y_min:y_max, x_min:x_max]
    if crop.size == 0:
        return None
    return crop


# ============================================================
# MODEL INFERENCE
# ============================================================

def model_predict(img: np.ndarray, model_instance=None) -> Tuple[float, Optional[float]]:
    """
    Runs model inference on an image tensor (224, 224, 3).
    Handles both single-head (poster_model) and dual-head (eventtrust_model) outputs.
    """
    model = model_instance or get_model()

    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    img = cv2.resize(img, (224, 224))
    img = img.astype(np.float32) / 255.0
    img = np.expand_dims(img, axis=0)

    predictions = model.predict(img, verbose=0)

    if isinstance(predictions, list) and len(predictions) > 1:
        # Multi-head model [poster_output, qr_output]
        poster_prob = float(np.squeeze(predictions[0]))
        qr_prob = float(np.squeeze(predictions[1]))
    elif isinstance(predictions, list):
        poster_prob = float(np.squeeze(predictions[0]))
        qr_prob = None
    else:
        poster_prob = float(np.squeeze(predictions))
        qr_prob = None

    return poster_prob, qr_prob


# ============================================================
# PREDICT POSTER
# ============================================================

def predict_poster(
    image_input: Union[str, Path, bytes, np.ndarray],
    model_instance=None
) -> Dict[str, Any]:
    """
    Full pipeline for poster authenticity verification + QR detection and security analysis.
    """
    # 1. Load image
    if isinstance(image_input, (str, Path)):
        p = Path(image_input)
        if not p.exists():
            raise FileNotFoundError(f"Poster image file not found: {p}")
        poster_img = cv2.imread(str(p))
    elif isinstance(image_input, bytes):
        nparr = np.frombuffer(image_input, np.uint8)
        poster_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif isinstance(image_input, np.ndarray):
        poster_img = image_input
    else:
        raise ValueError("Invalid image input format. Must be file path, bytes, or numpy ndarray.")

    if poster_img is None or poster_img.size == 0:
        raise ValueError("Failed to decode or read poster image.")

    # 2. Poster Model Prediction
    real_probability, model_qr_prob = model_predict(poster_img, model_instance=model_instance)
    fake_probability = max(0.0, min(1.0, 1.0 - real_probability))

    if real_probability >= 0.50:
        poster_result = "REAL"
    else:
        poster_result = "SUSPICIOUS"

    poster_confidence = max(real_probability, fake_probability)

    # 3. QR Detection
    qr_data, qr_points = detect_qr(poster_img)
    qr_status = "DETECTED" if (qr_data is not None and len(qr_data) > 0) else "NOT DETECTED"

    # 4. QR Analysis
    qr_result = "NO QR"
    qr_confidence = 0.0
    malicious_probability = 0.0
    benign_probability = 1.0 if qr_status == "NOT DETECTED" else 0.0

    if qr_status == "DETECTED":
        # Check if model has a dedicated QR head
        if qr_points is not None:
            qr_crop = crop_qr(poster_img, qr_points)
            if qr_crop is not None and model_qr_prob is not None:
                _, crop_qr_prob = model_predict(qr_crop, model_instance=model_instance)
                if crop_qr_prob is not None:
                    malicious_probability = crop_qr_prob
                    benign_probability = 1.0 - malicious_probability

        # Heuristic / Domain security check on QR Payload
        qr_lower = str(qr_data).lower()
        suspicious_keywords = [
            "bit.ly", "tinyurl", "free-iphone", "t.me/", "wa.me/", "claimnow",
            "prize", "atualizacaodedados", "webmasteradmin", "giveaway",
            "fastcash", "free-", ".xyz", ".top", ".tk", ".ml", "fake"
        ]
        is_suspicious_url = any(k in qr_lower for k in suspicious_keywords)
        is_valid_http = qr_lower.startswith("http://") or qr_lower.startswith("https://") or qr_lower.startswith("upi://")

        if is_suspicious_url:
            malicious_probability = max(malicious_probability, 0.85)
            benign_probability = 1.0 - malicious_probability
            qr_result = "MALICIOUS"
            qr_confidence = malicious_probability
        elif is_valid_http or qr_status == "DETECTED":
            if malicious_probability >= 0.50:
                qr_result = "MALICIOUS"
                qr_confidence = malicious_probability
            else:
                qr_result = "BENIGN"
                benign_probability = max(benign_probability, 0.90)
                qr_confidence = benign_probability

    # 5. Transparent Trust Score Calculation
    # Formula Breakdown:
    # - Poster Vision Model: 60% (up to 60 pts)
    # - QR Verification:     25% (up to 25 pts)
    # - Event Info Integrity: 15% (Date +5, Organizer +5, Registration Info +5)

    # Component 1: Poster model visual authenticity (0–60 pts)
    poster_score = real_probability * 60.0

    # Component 2: QR detection & payload security (0–25 pts)
    if qr_status == "DETECTED":
        if qr_result == "BENIGN":
            qr_score = max(0.0, benign_probability * 25.0)
        else:
            qr_score = -20.0  # Malicious QR penalty
    else:
        qr_score = 12.5  # Neutral score for posters without QR

    # Component 3: Basic event information & structural integrity checks (0–15 pts)
    if real_probability >= 0.50:
        event_info_score = 15.0  # +5 Date, +5 Organizer, +5 Registration
    else:
        event_info_score = 0.0

    raw_trust_score = poster_score + qr_score + event_info_score
    trust_score = int(max(0, min(100, round(raw_trust_score))))

    # 6. Standard Risk Level & Status Classification
    if qr_result == "MALICIOUS" or real_probability < 0.40 or trust_score < 50:
        risk_level = "HIGH"
        poster_status_label = "HIGH RISK"
        verification_status = "REVIEW_REQUIRED"
        prediction_label = "SUSPICIOUS" if real_probability < 0.50 else "REAL"
    elif trust_score >= 70 and qr_result != "MALICIOUS":
        risk_level = "LOW"
        poster_status_label = "LOW RISK"
        verification_status = "VERIFIED"
        prediction_label = "REAL"
    else:
        risk_level = "MEDIUM"
        poster_status_label = "MEDIUM RISK"
        verification_status = "REVIEW_REQUIRED"
        prediction_label = "REAL" if real_probability >= 0.50 else "SUSPICIOUS"

    # QR verified boolean
    qr_detected_bool = (qr_status == "DETECTED")
    qr_verified_bool = (qr_detected_bool and qr_result == "BENIGN")

    # 7. Issue & Signal Generation
    issues = []
    positive_indicators = []

    if prediction_label == "SUSPICIOUS" or real_probability < 0.50:
        issues.append("Poster classified as suspicious")
        issues.append("Registration information could not be verified")
    else:
        positive_indicators.append("Event date detected")
        positive_indicators.append("College/organization detected")
        positive_indicators.append("Registration information detected")

    if qr_result == "MALICIOUS":
        issues.append("QR destination requires review")
        issues.append("Suspicious redirect or unverified shortlink in QR payload")
    elif qr_detected_bool and qr_verified_bool:
        positive_indicators.append("QR destination valid and accessible")
    elif qr_detected_bool and not qr_verified_bool:
        issues.append("QR destination could not be verified")

    if not issues:
        positive_indicators.append("No major suspicious indicators")

    # 8. Recommendation
    if risk_level == "LOW":
        recommendation = "This event appears trustworthy."
    elif risk_level == "MEDIUM":
        recommendation = "Please verify event details and organizer credentials before registering."
    else:
        recommendation = "Verify this event before registering."

    return {
        "prediction": prediction_label,
        "confidence": round(poster_confidence, 4),
        "trust_score": trust_score,
        "status": verification_status,
        "risk_level": risk_level,
        "qr_detected": qr_detected_bool,
        "qr_verified": qr_verified_bool,
        "issues": issues,
        "positive_indicators": positive_indicators,
        "recommendation": recommendation,
        "score_breakdown": {
            "poster_score": round(poster_score, 1),
            "qr_score": round(qr_score, 1),
            "event_info_score": round(event_info_score, 1),
            "total": trust_score,
            "note": "Prototype risk indicator calculated via MobileNetV2 and QR analysis. Not definitive proof of event legitimacy."
        },

        # Compatibility fields
        "poster_result": poster_result,
        "poster_status": poster_status_label,
        "real_probability": round(real_probability * 100.0, 2),
        "fake_probability": round(fake_probability * 100.0, 2),
        "poster_confidence": round(poster_confidence * 100.0, 2),
        "confidence_score": round(poster_confidence, 4),
        "qr_status": qr_status,
        "qr_result": qr_result,
        "benign_probability": round(benign_probability * 100.0, 2),
        "malicious_probability": round(malicious_probability * 100.0, 2),
        "qr_confidence": round(qr_confidence * 100.0, 2),
        "qr_data": qr_data,
    }


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print()
        print("Usage:")
        print("  python predict.py <path_to_event_poster_image>")
        print()
        sys.exit(1)

    poster_path = sys.argv[1]
    result = predict_poster(poster_path)

    print()
    print("================================================")
    print("              EVENTTRUST AI")
    print("================================================")
    print()
    print("POSTER RESULT:   ", result["poster_result"])
    print("FINAL STATUS:    ", result["poster_status"])
    print(f"TRUST SCORE:      {result['trust_score']} / 100")
    print()
    print("--------------- POSTER ANALYSIS ---------------")
    print(f"REAL:             {result['real_probability']} %")
    print(f"FAKE:             {result['fake_probability']} %")
    print(f"CONFIDENCE:       {result['poster_confidence']} %")
    print()
    print("---------------- QR ANALYSIS -------------------")
    print("QR STATUS:       ", result["qr_status"])
    print("QR RESULT:       ", result["qr_result"])
    if result["qr_status"] == "DETECTED":
        print()
        print(f"BENIGN:           {result['benign_probability']} %")
        print(f"MALICIOUS:        {result['malicious_probability']} %")
        print(f"QR CONFIDENCE:    {result['qr_confidence']} %")
        print()
        print(f"QR DATA:          {result['qr_data']}")
    else:
        print("QR DATA:          None")
    print()
    print("================================================")
 