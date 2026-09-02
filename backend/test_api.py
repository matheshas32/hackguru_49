import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.main import app
from backend.schemas import PosterScanResponse, UnstopVerificationResponse

def test_health(client):
    print("\n--- 1. Testing Health Endpoint ---")
    response = client.get("/api/health")
    print(f"Status: {response.status_code}, Body: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["model_loaded"] is True
    print("[PASS] Health check passed.")

def test_verify_real_poster(client):
    print("\n--- 2. Testing Verify Poster (Real Sample) ---")
    real_img = ROOT_DIR / "dataset" / "real" / "real_01.jpg"
    assert real_img.exists(), f"Image not found at {real_img}"

    with open(real_img, "rb") as f:
        response = client.post(
            "/api/verify-poster",
            files={"file": ("real_01.jpg", f, "image/jpeg")}
        )

    print(f"Status: {response.status_code}")
    data = response.json()
    print("Response Data:", data)
    assert response.status_code == 200
    # Test EventTrust AI required fields
    assert "prediction" in data
    assert "confidence" in data
    assert "trust_score" in data
    assert "status" in data
    assert "risk_level" in data
    assert "qr_detected" in data
    assert "qr_verified" in data
    assert "issues" in data
    assert isinstance(data["issues"], list)
    assert data["prediction"] == "REAL"
    assert data["status"] in ["VERIFIED", "REVIEW_REQUIRED"]
    assert data["risk_level"] in ["LOW", "MEDIUM"]
    print("[PASS] Real poster verification passed with full EventTrust schema.")

def test_verify_fake_poster(client):
    print("\n--- 3. Testing Verify Poster (Fake Sample) ---")
    fake_img = ROOT_DIR / "backend" / "static" / "images" / "sample_fake_event.png"
    if not fake_img.exists():
        fake_img = ROOT_DIR / "dataset" / "fake" / "fake_01.jpg"
    assert fake_img.exists(), f"Image not found at {fake_img}"

    with open(fake_img, "rb") as f:
        response = client.post(
            "/api/verify-poster",
            files={"file": (fake_img.name, f, "image/png")}
        )

    print(f"Status: {response.status_code}")
    data = response.json()
    print("Response Data:", data)
    assert response.status_code == 200
    assert "prediction" in data
    assert "trust_score" in data
    assert "risk_level" in data
    assert "issues" in data
    print(f"[PASS] Fake poster verification passed (Score: {data['trust_score']}, Risk: {data['risk_level']}).")

def test_verify_qr_poster(client):
    print("\n--- 4. Testing Verify Poster with QR Code ---")
    qr_img = ROOT_DIR / "qr_dataset" / "QR codes" / "benign" / "benign" / "benign_0.png"
    assert qr_img.exists(), f"Image not found at {qr_img}"

    with open(qr_img, "rb") as f:
        response = client.post(
            "/api/verify-poster",
            files={"file": (qr_img.name, f, "image/png")}
        )

    print(f"Status: {response.status_code}")
    data = response.json()
    print("Response Data:", data)
    assert response.status_code == 200
    assert data["qr_detected"] is True
    assert data["qr_status"] == "DETECTED"
    assert data["qr_data"] is not None
    assert "qr_verified" in data
    print(f"[PASS] QR detection verified with decoded data: {data['qr_data']} (Verified: {data['qr_verified']})")

def test_verify_unstop_url(client):
    print("\n--- 5. Testing Verify Unstop Event URL ---")
    # Test with mock fetch to ensure pipeline end-to-end verification works cleanly
    test_img = ROOT_DIR / "dataset" / "real" / "real_01.jpg"
    with open(test_img, "rb") as f:
        img_bytes = f.read()

    async def mock_fetch(url):
        return {
            "title": "IIT Madras Shaastra AI Hackathon 2026",
            "college": "IIT Madras",
            "description": "Premier national hackathon hosted on Unstop for AI innovators.",
            "poster_url": "https://d8it4huxumps7.cloudfront.net/uploads/images/hackathon-banner.jpg",
            "source_url": url,
        }

    async def mock_download(url):
        return img_bytes

    with patch("backend.services.unstop_service.unstop_service.fetch_event_metadata", side_effect=mock_fetch), \
         patch("backend.services.unstop_service.unstop_service.download_image_bytes", side_effect=mock_download):
        
        response = client.post(
            "/api/verify-url",
            json={"url": "https://unstop.com/hackathons/iit-madras-shaastra-ai-hackathon-2026"}
        )

    print(f"Status: {response.status_code}")
    data = response.json()
    print("Unstop Verification Data:", data)
    assert response.status_code == 200
    assert "url" in data
    assert "title" in data
    assert "verification" in data
    assert data["verification"]["poster_result"] in ["REAL", "SUSPICIOUS"]
    assert data["verification"]["real_probability"] >= 0.0
    print("[PASS] Unstop URL verification passed.")

def test_create_event_with_poster(client):
    print("\n--- 6. Testing Create College Event with Poster ---")
    poster_path = ROOT_DIR / "dataset" / "real" / "real_02.jpg"
    assert poster_path.exists()

    with open(poster_path, "rb") as f:
        response = client.post(
            "/api/events",
            data={
                "title": "Inter-University Autonomous Robotics Challenge 2026",
                "college": "Anna University, CEG Campus",
                "description": "Annual student robotics competition featuring maze solving, line following, and drone navigation.",
                "category": "Symposium",
                "event_date": "2026-10-15 10:00 AM",
                "venue": "Tag Auditorium, CEG Campus",
                "registration_url": "https://robotics.ceg.edu/register",
                "organizer_contact": "robotics-club@ceg.edu"
            },
            files={"poster": ("robotics_poster.jpg", f, "image/jpeg")}
        )

    print(f"Status: {response.status_code}")
    data = response.json()
    print("Created Event:", data)
    assert response.status_code == 201
    assert "id" in data
    assert "verification" in data
    assert data["verification"]["poster_result"] in ["REAL", "SUSPICIOUS"]
    print("[PASS] Event creation with poster verification passed.")

def test_list_and_filter_events(client):
    print("\n--- 7. Testing List and Filter Events ---")
    response = client.get("/api/events")
    assert response.status_code == 200
    data = response.json()
    print(f"Total events found: {data['total']}")
    assert data["total"] >= 1

    # Test category filter
    resp_hackathon = client.get("/api/events?category=Hackathon")
    assert resp_hackathon.status_code == 200
    print(f"Hackathons found: {len(resp_hackathon.json()['events'])}")

    # Test status filter
    resp_real = client.get("/api/events?status=REAL")
    assert resp_real.status_code == 200
    print(f"Verified Real events found: {len(resp_real.json()['events'])}")
    print("[PASS] Event listing and filtering passed.")

def test_stats(client):
    print("\n--- 8. Testing Stats Endpoint ---")
    response = client.get("/api/stats")
    assert response.status_code == 200
    stats = response.json()
    print("Stats Response:", stats)
    assert "total_events" in stats
    assert "verified_real_events" in stats
    assert "average_trust_score" in stats
    print("[PASS] Stats check passed.")

if __name__ == "__main__":
    print("=========================================================")
    print(" RUNNING INTEGRATION TESTS FOR EVENTTRUST AI BACKEND")
    print("=========================================================")
    with TestClient(app) as client:
        test_health(client)
        test_verify_real_poster(client)
        test_verify_fake_poster(client)
        test_verify_qr_poster(client)
        test_verify_unstop_url(client)
        test_create_event_with_poster(client)
        test_list_and_filter_events(client)
        test_stats(client)
    print("\n=========================================================")
    print(" ALL TESTS PASSED SUCCESSFULLY! [OK]")
    print("=========================================================")
