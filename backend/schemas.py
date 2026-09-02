from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class PosterScanResponse(BaseModel):
    # Standard EventTrust AI fields
    prediction: str = Field(..., description="Overall prediction: REAL or FAKE")
    confidence: float = Field(..., description="Model confidence as a decimal (0.0 - 1.0)")
    trust_score: int = Field(..., description="Calculated authenticity trust score out of 100")
    status: str = Field(..., description="Verification status: VERIFIED, REVIEW_REQUIRED, or SUSPICIOUS")
    risk_level: str = Field(..., description="Risk category: LOW, MEDIUM, or HIGH")
    qr_detected: bool = Field(..., description="Whether a QR code was detected in the poster")
    qr_verified: bool = Field(..., description="Whether the QR code was safely verified")
    issues: List[str] = Field(default_factory=list, description="List of detected suspicious issues or risk factors")
    positive_indicators: List[str] = Field(default_factory=list, description="List of verified positive authenticity indicators")
    recommendation: Optional[str] = Field(None, description="Actionable recommendation for event publishing")

    # Detailed metrics & compatibility fields
    poster_result: str = Field(..., description="Classification result: REAL or SUSPICIOUS")
    poster_status: str = Field(..., description="Overall risk status: LOW RISK, MEDIUM RISK, HIGH RISK")
    real_probability: float = Field(..., description="Model probability percentage of being authentic (0-100%)")
    fake_probability: float = Field(..., description="Model probability percentage of being fake (0-100%)")
    poster_confidence: float = Field(..., description="Confidence score percentage (0-100%)")
    confidence_score: float = Field(..., description="Confidence score as decimal (0.0-1.0)")
    qr_status: str = Field(..., description="QR Detection status: DETECTED or NOT DETECTED")
    qr_result: str = Field(..., description="QR Security status: BENIGN, MALICIOUS, or NO QR")
    benign_probability: float = Field(default=0.0, description="Benign probability percentage")
    malicious_probability: float = Field(default=0.0, description="Malicious probability percentage")
    qr_confidence: float = Field(default=0.0, description="QR classification confidence percentage")
    qr_data: Optional[str] = Field(None, description="Decoded QR payload or URL")
    filename: Optional[str] = Field(None, description="Saved filename of the uploaded poster")
    poster_url: Optional[str] = Field(None, description="Accessible URL for the uploaded poster image")


class UrlVerificationRequest(BaseModel):
    url: str = Field(..., description="Web link of the Unstop event or competition (e.g., https://unstop.com/hackathons/...)")


class UnstopVerificationResponse(BaseModel):
    url: str = Field(..., description="Target Unstop event URL")
    title: str = Field(..., description="Extracted event title")
    college: str = Field(..., description="Extracted college or organization host")
    description: str = Field(..., description="Extracted event description")
    extracted_poster_url: str = Field(..., description="URL of the extracted event poster image")
    verification: PosterScanResponse = Field(..., description="Authenticity model inference and QR scan results")


class EventBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=200, description="Title of the college event")
    college: str = Field(..., min_length=2, max_length=200, description="Organizing college/university name")
    description: str = Field(..., min_length=5, description="Full description of the event")
    category: str = Field(default="Technical", description="Category: Hackathon, Symposium, Workshop, Cultural, Sports, etc.")
    event_date: str = Field(..., description="Date and time of the event (e.g., 2026-09-15 10:00 AM)")
    venue: str = Field(..., description="Event venue or location on campus")
    registration_url: Optional[str] = Field(None, description="Official registration or ticketing link")
    organizer_contact: Optional[str] = Field(None, description="Organizer email or phone number")


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: str
    created_at: str
    poster_url: Optional[str] = None
    verification: PosterScanResponse


class EventListResponse(BaseModel):
    total: int
    events: List[EventResponse]


class StatsResponse(BaseModel):
    total_events: int
    verified_real_events: int
    suspicious_events: int
    total_posters_scanned: int
    qr_detected_count: int
    average_trust_score: float
