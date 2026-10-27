import os

from app import db
from app.models import Alert, CameraPoint, Message, Task, User, ZoneStatus

HAIL_LAT, HAIL_LNG = 27.5114, 41.7208


def seed_database() -> None:
    if User.query.count() > 0:
        return

    password_variables = ("MADAR_ADMIN_PASSWORD", "MADAR_MANAGER_PASSWORD", "MADAR_OFFICER_PASSWORD")
    configured_passwords = [os.environ.get(name, "") for name in password_variables]
    missing = [name for name, password in zip(password_variables, configured_passwords) if not password.strip()]
    if missing:
        raise RuntimeError("Set initial account passwords before first startup: " + ", ".join(missing))

    users = [
        User(name="System Administrator", email="admin@madaramney.sa", role="admin", badge_code="ADM-001",
             phone="+966500000001", last_lat=HAIL_LAT, last_lng=HAIL_LNG),
        User(name="Operations Manager", email="manager@madaramney.sa", role="manager", badge_code="MGR-001",
             phone="+966500000002", last_lat=HAIL_LAT + 0.002, last_lng=HAIL_LNG + 0.001),
        User(name="Field Officer Amjad", email="officer1@madaramney.sa", role="officer", badge_code="OFF-101",
             phone="+966500000101", last_lat=HAIL_LAT + 0.004, last_lng=HAIL_LNG - 0.002),
        User(name="Field Officer Yasmeen", email="officer2@madaramney.sa", role="officer", badge_code="OFF-102",
             phone="+966500000102", last_lat=HAIL_LAT - 0.003, last_lng=HAIL_LNG + 0.003),
        User(name="Field Officer Fay", email="officer3@madaramney.sa", role="officer", badge_code="OFF-103",
             phone="+966500000103", last_lat=HAIL_LAT + 0.001, last_lng=HAIL_LNG - 0.004),
    ]
    admin_password, manager_password, officer_password = configured_passwords
    passwords = [admin_password, manager_password, officer_password, officer_password, officer_password]
    for u, p in zip(users, passwords):
        u.set_password(p)
    db.session.add_all(users)
    db.session.flush()

    cameras = [
        CameraPoint(name="Main Gate North", code="CAM-N01", description="Primary northern access checkpoint",
                    lat=HAIL_LAT + 0.004, lng=HAIL_LNG - 0.002, is_online=True, zone_status="green",
                    assigned_officer_id=users[2].id),
        CameraPoint(name="East Perimeter", code="CAM-E02", description="Eastern fence line surveillance",
                    lat=HAIL_LAT - 0.003, lng=HAIL_LNG + 0.003, is_online=True, zone_status="amber",
                    assigned_officer_id=users[3].id),
        CameraPoint(name="Control Building", code="CAM-C03", description="Operations building entrance",
                    lat=HAIL_LAT + 0.001, lng=HAIL_LNG - 0.004, is_online=False, zone_status="green",
                    assigned_officer_id=users[4].id),
        CameraPoint(name="South Parking", code="CAM-S04", description="Visitor parking lot",
                    lat=HAIL_LAT - 0.005, lng=HAIL_LNG - 0.001, is_online=True, zone_status="green"),
        CameraPoint(name="Warehouse Zone", code="CAM-W05", description="Critical storage facility",
                    lat=HAIL_LAT + 0.006, lng=HAIL_LNG + 0.004, is_online=True, zone_status="red"),
    ]
    db.session.add_all(cameras)
    db.session.flush()

    db.session.add_all([
        ZoneStatus(name="Gate Sector A", code="ZONE-A", lat=HAIL_LAT + 0.004, lng=HAIL_LNG - 0.002, radius_m=150, color="green"),
        ZoneStatus(name="Perimeter East", code="ZONE-E", lat=HAIL_LAT - 0.003, lng=HAIL_LNG + 0.003, radius_m=180, color="amber", notes="Elevated motion activity"),
        ZoneStatus(name="Critical Warehouse", code="ZONE-W", lat=HAIL_LAT + 0.006, lng=HAIL_LNG + 0.004, radius_m=120, color="red", notes="AI flagged potential breach"),
        ZoneStatus(name="Parking South", code="ZONE-S", lat=HAIL_LAT - 0.005, lng=HAIL_LNG - 0.001, radius_m=140, color="green"),
    ])

    alerts = [
        Alert(title="Perimeter motion anomaly", description="AI detected unusual movement near East Perimeter fence.",
              severity="high", status="open", confidence=0.87, threat_type="perimeter_breach",
              lat=cameras[1].lat, lng=cameras[1].lng, camera_id=cameras[1].id, officer_id=users[3].id),
        Alert(title="Warehouse unauthorized access pattern", description="Behavioral model flagged possible unauthorized access attempt.",
              severity="critical", status="acknowledged", confidence=0.93, threat_type="unauthorized_access",
              lat=cameras[4].lat, lng=cameras[4].lng, camera_id=cameras[4].id),
        Alert(title="Loitering near Main Gate", description="Prolonged presence detected outside authorized waiting zone.",
              severity="medium", status="resolved", confidence=0.71, threat_type="loitering",
              lat=cameras[0].lat, lng=cameras[0].lng, camera_id=cameras[0].id, officer_id=users[2].id),
    ]
    db.session.add_all(alerts)
    db.session.flush()

    db.session.add_all([
        Task(title="Inspect East Perimeter fence", description="Verify sensor and camera alignment after AI alert.",
             status="in_progress", priority="high", assignee_id=users[3].id, created_by_id=users[1].id, related_alert_id=alerts[0].id),
        Task(title="Secure Warehouse Zone access", description="Lock secondary doors and report badge scans.",
             status="pending", priority="critical", assignee_id=users[4].id, created_by_id=users[1].id, related_alert_id=alerts[1].id),
        Task(title="Routine Main Gate check", description="Confirm visitor queue clearance.",
             status="completed", priority="medium", assignee_id=users[2].id, created_by_id=users[0].id),
    ])

    db.session.add_all([
        Message(sender_id=users[1].id, content="All units: Warehouse zone elevated to RED. Stand by for instructions."),
        Message(sender_id=users[3].id, content="Officer Yasmeen on site at East Perimeter. Visual clear so far."),
        Message(sender_id=users[0].id, content="Admin: Keep streams active. AI module is online."),
    ])
    db.session.commit()
