"""Simple AI threat simulation for the Flask prototype."""
from __future__ import annotations

import hashlib
import random


def simulate_threat(force: bool = True) -> dict:
    threats = [
        ("loitering", "medium", 0.72),
        ("crowd_density", "medium", 0.76),
        ("unauthorized_access", "high", 0.86),
        ("abandoned_object", "high", 0.84),
        ("aggressive_motion", "critical", 0.91),
        ("perimeter_breach", "critical", 0.93),
    ]
    if not force and random.random() < 0.35:
        return {
            "threat_detected": False,
            "threat_type": "normal",
            "confidence": 0.88,
            "severity": "low",
            "details": "No behavioral anomaly detected",
        }
    threat_type, severity, confidence = random.choice(threats)
    return {
        "threat_detected": True,
        "threat_type": threat_type,
        "confidence": confidence,
        "severity": severity,
        "details": f"Pattern recognition flagged '{threat_type}'",
    }


def analyze_image_bytes(data: bytes, filename: str = "frame.jpg") -> dict:
    digest = int(hashlib.sha256(data[:2048] + filename.encode()).hexdigest()[:8], 16)
    score = (digest % 100) / 100.0
    if score < 0.25:
        return {
            "threat_detected": False,
            "threat_type": "normal",
            "confidence": round(0.7 + score * 0.2, 3),
            "severity": "low",
            "details": "Frame analysis: normal activity",
        }
    threats = [
        ("loitering", "medium"),
        ("unauthorized_access", "high"),
        ("perimeter_breach", "critical"),
        ("abandoned_object", "high"),
    ]
    threat_type, severity = threats[digest % len(threats)]
    return {
        "threat_detected": True,
        "threat_type": threat_type,
        "confidence": round(0.65 + score * 0.3, 3),
        "severity": severity,
        "details": f"OpenCV/heuristic analysis flagged '{threat_type}'",
    }
