from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="officer")  # admin, manager, officer
    badge_code = db.Column(db.String(40), unique=True, nullable=False)
    phone = db.Column(db.String(40))
    is_active = db.Column(db.Boolean, default=True)
    last_lat = db.Column(db.Float)
    last_lng = db.Column(db.Float)
    last_seen = db.Column(db.DateTime)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_command(self) -> bool:
        return self.role in ("admin", "manager")


class CameraPoint(db.Model):
    __tablename__ = "camera_points"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    description = db.Column(db.Text)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    is_online = db.Column(db.Boolean, default=False)
    zone_status = db.Column(db.String(20), default="green")
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey("users.id"))


class Alert(db.Model):
    __tablename__ = "alerts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    severity = db.Column(db.String(20), default="medium")
    status = db.Column(db.String(20), default="open")
    confidence = db.Column(db.Float, default=0.0)
    threat_type = db.Column(db.String(80), default="anomaly")
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    camera_id = db.Column(db.Integer, db.ForeignKey("camera_points.id"))
    officer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime)


class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room = db.Column(db.String(80), default="ops")
    content = db.Column(db.Text, nullable=False)
    is_encrypted = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sender = db.relationship("User")


class StreamSession(db.Model):
    __tablename__ = "stream_sessions"
    id = db.Column(db.Integer, primary_key=True)
    camera_id = db.Column(db.Integer, db.ForeignKey("camera_points.id"))
    officer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_token = db.Column(db.String(80), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")
    priority = db.Column(db.String(20), default="medium")
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    related_alert_id = db.Column(db.Integer, db.ForeignKey("alerts.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ZoneStatus(db.Model):
    __tablename__ = "zone_statuses"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(40), unique=True, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    radius_m = db.Column(db.Float, default=120.0)
    color = db.Column(db.String(20), default="green")
    notes = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)