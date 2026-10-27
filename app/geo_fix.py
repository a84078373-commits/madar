"""Update seed coordinates to realistic Hail city locations for the map."""
from app import db
from app.models import Alert, CameraPoint, User, ZoneStatus

# Realistic points around Hail / University of Ha'il area
GEO = {
    "CAM-N01": (27.5318, 41.6952, "البوابة الشمالية الرئيسية"),
    "CAM-E02": (27.5261, 41.7084, "السور الشرقي"),
    "CAM-C03": (27.5289, 41.6998, "مبنى العمليات"),
    "CAM-S04": (27.5224, 41.6971, "مواقف الجنوب"),
    "CAM-W05": (27.5346, 41.7055, "مستودع المنطقة الحرجة"),
    "ZONE-A": (27.5318, 41.6952, 160),
    "ZONE-E": (27.5261, 41.7084, 180),
    "ZONE-W": (27.5346, 41.7055, 140),
    "ZONE-S": (27.5224, 41.6971, 150),
    "OFF-101": (27.5305, 41.6960),
    "OFF-102": (27.5255, 41.7070),
    "OFF-103": (27.5295, 41.6985),
    "ADM-001": (27.5289, 41.6998),
    "MGR-001": (27.5298, 41.7010),
}


def apply_realistic_geo() -> None:
    for cam in CameraPoint.query.all():
        if cam.code in GEO:
            lat, lng, name_ar = GEO[cam.code]
            cam.lat, cam.lng = lat, lng
            if name_ar and (not cam.description or "checkpoint" in (cam.description or "").lower() or "surveillance" in (cam.description or "").lower() or "parking" in (cam.description or "").lower() or "facility" in (cam.description or "").lower() or "entrance" in (cam.description or "").lower()):
                cam.name = name_ar if cam.code.startswith("CAM") else cam.name

    # Prefer Arabic operational names for demo realism
    rename = {
        "CAM-N01": "كاميرا البوابة الشمالية",
        "CAM-E02": "كاميرا السور الشرقي",
        "CAM-C03": "كاميرا مبنى العمليات",
        "CAM-S04": "كاميرا مواقف الجنوب",
        "CAM-W05": "كاميرا المستودع الحرج",
    }
    for cam in CameraPoint.query.all():
        if cam.code in rename:
            cam.name = rename[cam.code]

    for zone in ZoneStatus.query.all():
        if zone.code in GEO:
            lat, lng, radius = GEO[zone.code]
            zone.lat, zone.lng, zone.radius_m = lat, lng, radius
    zone_names = {
        "ZONE-A": "قطاع البوابة أ",
        "ZONE-E": "المحيط الشرقي",
        "ZONE-W": "المستودع الحرج",
        "ZONE-S": "مواقف الجنوب",
    }
    for zone in ZoneStatus.query.all():
        if zone.code in zone_names:
            zone.name = zone_names[zone.code]

    for user in User.query.all():
        if user.badge_code in GEO:
            user.last_lat, user.last_lng = GEO[user.badge_code]

    # Keep alerts pinned to related cameras
    for alert in Alert.query.all():
        if alert.camera_id:
            cam = db.session.get(CameraPoint, alert.camera_id)
            if cam:
                alert.lat, alert.lng = cam.lat, cam.lng

    db.session.commit()
