import json
import secrets
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.ai import simulate_threat
from app.auth import role_required
from app.models import Alert, CameraPoint, Message, StreamSession, Task, User, ZoneStatus

main_bp = Blueprint("main", __name__)


def _stats():
    total_cameras = CameraPoint.query.count()
    online = CameraPoint.query.filter_by(is_online=True).count()
    open_alerts = Alert.query.filter(Alert.status.in_(["open", "acknowledged"])).count()
    return {
        "online_cameras": online,
        "total_cameras": total_cameras,
        "open_alerts": open_alerts,
        "critical_alerts": Alert.query.filter(
            Alert.severity == "critical", Alert.status.in_(["open", "acknowledged"])
        ).count(),
        "active_officers": User.query.filter_by(role="officer", is_active=True).count(),
        "active_streams": StreamSession.query.filter_by(is_active=True).count(),
        "zones_red": ZoneStatus.query.filter_by(color="red").count(),
        "vital_locations": ZoneStatus.query.count(),
    }


def _map_payload():
    cameras = CameraPoint.query.order_by(CameraPoint.id).all()
    zones = ZoneStatus.query.order_by(ZoneStatus.id).all()
    alerts = Alert.query.filter(Alert.status.in_(["open", "acknowledged"])).all()
    officers = User.query.filter_by(role="officer", is_active=True).all()
    return {
        "cameras": cameras,
        "zones": zones,
        "alerts": alerts,
        "officers": officers,
        "cameras_json": json.dumps(
            [
                {
                    "id": c.id,
                    "name": c.name,
                    "code": c.code,
                    "lat": c.lat,
                    "lng": c.lng,
                    "online": bool(c.is_online),
                    "zone": c.zone_status,
                }
                for c in cameras
            ],
            ensure_ascii=False,
        ),
        "zones_json": json.dumps(
            [
                {
                    "name": z.name,
                    "lat": z.lat,
                    "lng": z.lng,
                    "radius": z.radius_m,
                    "color": z.color,
                }
                for z in zones
            ],
            ensure_ascii=False,
        ),
        "alerts_json": json.dumps(
            [
                {
                    "title": a.title,
                    "lat": a.lat,
                    "lng": a.lng,
                    "severity": a.severity,
                }
                for a in alerts
                if a.lat is not None and a.lng is not None
            ],
            ensure_ascii=False,
        ),
        "officers_json": json.dumps(
            [
                {
                    "name": o.name,
                    "lat": o.last_lat,
                    "lng": o.last_lng,
                    "badge": o.badge_code,
                }
                for o in officers
                if o.last_lat is not None and o.last_lng is not None
            ],
            ensure_ascii=False,
        ),
    }


# ===================== Command (Web Dashboard) =====================

@main_bp.route("/dashboard")
@login_required
@role_required("admin", "manager")
def dashboard():
    stats = _stats()
    recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(5).all()
    risk_level = min(95, 28 + stats["open_alerts"] * 8 + stats["critical_alerts"] * 12)
    events = []
    for a in recent_alerts[:4]:
        tone = "danger" if a.severity in ("critical", "high") else "info"
        events.append({
            "title": a.title,
            "time": a.created_at.strftime("%H:%M") if a.created_at else "",
            "tone": tone,
            "icon": "fa-triangle-exclamation" if tone == "danger" else "fa-circle-info",
        })
    for t in Task.query.order_by(Task.created_at.desc()).limit(3).all():
        events.append({
            "title": t.title,
            "time": t.created_at.strftime("%H:%M") if t.created_at else "",
            "tone": "ok" if t.status == "completed" else "info",
            "icon": "fa-check" if t.status == "completed" else "fa-user-shield",
        })
    return render_template(
        "dashboard.html",
        stats=stats,
        recent_alerts=recent_alerts,
        risk_level=risk_level,
        events=events[:6],
        **_map_payload(),
    )


@main_bp.route("/map")
@login_required
@role_required("admin", "manager")
def map_view():
    return render_template("map.html", **_map_payload())


@main_bp.route("/incidents")
@login_required
@role_required("admin", "manager")
def incidents():
    items = (
        Alert.query.filter(Alert.severity.in_(["high", "critical"]))
        .order_by(Alert.created_at.desc())
        .all()
    )
    return render_template("incidents.html", incidents=items)


@main_bp.route("/reports")
@login_required
@role_required("admin", "manager")
def reports():
    return render_template("reports.html", stats=_stats())


@main_bp.route("/reports/export.csv")
@login_required
@role_required("admin", "manager")
def reports_csv():
    from flask import Response

    stats = _stats()
    lines = [
        "metric,value",
        f"online_cameras,{stats['online_cameras']}",
        f"total_cameras,{stats['total_cameras']}",
        f"open_alerts,{stats['open_alerts']}",
        f"critical_alerts,{stats['critical_alerts']}",
        f"active_officers,{stats['active_officers']}",
        f"active_streams,{stats['active_streams']}",
        f"vital_locations,{stats['vital_locations']}",
    ]
    return Response(
        "\n".join(lines),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=madar_amney_report.csv"},
    )


@main_bp.route("/settings")
@login_required
@role_required("admin", "manager")
def settings():
    return render_template("settings.html")


@main_bp.route("/alerts", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def alerts():
    if request.method == "POST":
        alert_id = int(request.form["alert_id"])
        status = request.form["status"]
        alert = db.session.get(Alert, alert_id)
        if alert:
            alert.status = status
            if status in ("resolved", "dismissed"):
                alert.resolved_at = datetime.utcnow()
            db.session.commit()
            flash("تم تحديث حالة التنبيه.", "success")
        return redirect(url_for("main.alerts"))
    q = Alert.query.order_by(Alert.created_at.desc())
    severity = request.args.get("severity")
    status = request.args.get("status")
    if severity:
        q = q.filter(Alert.severity == severity)
    if status:
        q = q.filter(Alert.status == status)
    return render_template("alerts.html", alerts=q.all())


@main_bp.route("/cameras", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def cameras():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            code = request.form.get("code", "").strip()
            name = request.form.get("name", "").strip()
            if name and code and not CameraPoint.query.filter_by(code=code).first():
                db.session.add(
                    CameraPoint(
                        name=name,
                        code=code,
                        description=request.form.get("description"),
                        lat=float(request.form.get("lat") or 27.5114),
                        lng=float(request.form.get("lng") or 41.7208),
                        is_online=False,
                        zone_status="green",
                    )
                )
                db.session.commit()
                flash("Camera created / تم إضافة الكاميرا", "success")
            else:
                flash("Invalid camera data or duplicate code", "danger")
        elif action == "update":
            cam = db.session.get(CameraPoint, int(request.form["camera_id"]))
            if cam:
                cam.name = request.form.get("name", cam.name).strip() or cam.name
                cam.description = request.form.get("description", cam.description)
                cam.lat = float(request.form.get("lat") or cam.lat)
                cam.lng = float(request.form.get("lng") or cam.lng)
                db.session.commit()
                flash("Camera updated / تم التحديث", "success")
        elif action == "delete":
            cam = db.session.get(CameraPoint, int(request.form["camera_id"]))
            if cam:
                db.session.delete(cam)
                db.session.commit()
                flash("Camera deleted / تم الحذف", "success")
        else:
            cam = db.session.get(CameraPoint, int(request.form["camera_id"]))
            if cam and action == "toggle":
                cam.is_online = not cam.is_online
                db.session.commit()
                flash(f"Updated {cam.name}", "success")
            elif cam and action == "ai":
                result = simulate_threat(force=True)
                alert = Alert(
                    title=f"AI: {result['threat_type'].replace('_', ' ').title()}",
                    description=result["details"],
                    severity=result["severity"],
                    confidence=result["confidence"],
                    threat_type=result["threat_type"],
                    lat=cam.lat,
                    lng=cam.lng,
                    camera_id=cam.id,
                )
                if result["severity"] in ("high", "critical"):
                    cam.zone_status = "red"
                elif result["severity"] == "medium":
                    cam.zone_status = "amber"
                db.session.add(alert)
                db.session.commit()
                flash("AI alert created", "warning")
        return redirect(url_for("main.cameras"))

    q = request.args.get("q", "").strip().lower()
    status = request.args.get("status", "all")
    cams = CameraPoint.query.order_by(CameraPoint.id).all()
    if q:
        cams = [c for c in cams if q in c.name.lower() or q in c.code.lower()]
    if status == "online":
        cams = [c for c in cams if c.is_online]
    elif status == "offline":
        cams = [c for c in cams if not c.is_online]
    return render_template("cameras.html", cameras=cams, q=q, status=status)


@main_bp.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if content:
            db.session.add(Message(sender_id=current_user.id, content=content, is_encrypted=True))
            db.session.commit()
            flash("تم إرسال الرسالة المشفّرة.", "success")
        return redirect(url_for("main.chat" if current_user.is_command else "main.field_chat"))
    messages = Message.query.order_by(Message.created_at.asc()).all()
    if current_user.role == "officer":
        return render_template("field_chat.html", messages=messages)
    return render_template("chat.html", messages=messages)


@main_bp.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create" and current_user.is_command:
            title = request.form.get("title", "").strip()
            if title:
                db.session.add(
                    Task(
                        title=title,
                        description=request.form.get("description"),
                        priority=request.form.get("priority", "medium"),
                        assignee_id=int(request.form["assignee_id"]) if request.form.get("assignee_id") else None,
                        related_alert_id=int(request.form["alert_id"]) if request.form.get("alert_id") else None,
                        created_by_id=current_user.id,
                    )
                )
                db.session.commit()
                flash("تم إنشاء المهمة.", "success")
        elif action == "update":
            task = db.session.get(Task, int(request.form["task_id"]))
            if task and (current_user.is_command or task.assignee_id == current_user.id):
                task.status = request.form.get("status", task.status)
                db.session.commit()
                flash("تم تحديث المهمة.", "success")
        return redirect(url_for("main.tasks" if current_user.is_command else "main.field_tasks"))

    if current_user.role == "officer":
        items = Task.query.filter_by(assignee_id=current_user.id).order_by(Task.created_at.desc()).all()
        return render_template("field_tasks.html", tasks=items)

    items = Task.query.order_by(Task.created_at.desc()).all()
    officers = User.query.filter_by(role="officer", is_active=True).all()
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(20).all()
    return render_template("tasks.html", tasks=items, officers=officers, alerts=alerts)


@main_bp.route("/zones", methods=["GET", "POST"])
@login_required
@role_required("admin", "manager")
def zones():
    if request.method == "POST":
        zone = db.session.get(ZoneStatus, int(request.form["zone_id"]))
        if zone:
            zone.color = request.form.get("color", zone.color)
            zone.notes = request.form.get("notes", zone.notes)
            zone.updated_at = datetime.utcnow()
            db.session.commit()
            flash("تم تحديث حالة المنطقة.", "success")
        return redirect(url_for("main.zones"))
    return render_template("zones.html", **_map_payload())


@main_bp.route("/users")
@login_required
@role_required("admin", "manager")
def users():
    return render_template("users.html", users=User.query.order_by(User.id).all())


@main_bp.route("/ai/simulate", methods=["POST"])
@login_required
@role_required("admin", "manager")
def ai_simulate():
    camera_id = request.form.get("camera_id")
    cam = db.session.get(CameraPoint, int(camera_id)) if camera_id else CameraPoint.query.first()
    result = simulate_threat(force=True)
    alert = Alert(
        title=f"AI Simulated: {result['threat_type'].replace('_', ' ').title()}",
        description=result["details"],
        severity=result["severity"],
        confidence=result["confidence"],
        threat_type=result["threat_type"],
        lat=cam.lat if cam else None,
        lng=cam.lng if cam else None,
        camera_id=cam.id if cam else None,
    )
    if cam and result["severity"] in ("high", "critical"):
        cam.zone_status = "red"
    db.session.add(alert)
    db.session.commit()
    flash("تم توليد تنبيه AI للعرض.", "warning")
    return redirect(url_for("main.dashboard"))


# ===================== Field Officer (Web pages only) =====================

@main_bp.route("/field")
@login_required
@role_required("officer")
def field_home():
    my_tasks = Task.query.filter_by(assignee_id=current_user.id).order_by(Task.created_at.desc()).limit(5).all()
    open_alerts = Alert.query.filter(Alert.status.in_(["open", "acknowledged"])).order_by(Alert.created_at.desc()).limit(5).all()
    return render_template("field_home.html", tasks=my_tasks, alerts=open_alerts, stats=_stats())


@main_bp.route("/field/stream", methods=["GET", "POST"])
@login_required
@role_required("officer")
def field_stream():
    cameras = CameraPoint.query.order_by(CameraPoint.id).all()
    active = StreamSession.query.filter_by(officer_id=current_user.id, is_active=True).first()

    if request.method == "POST":
        action = request.form.get("action")
        if action == "start":
            camera_id = int(request.form["camera_id"]) if request.form.get("camera_id") else None
            cam = db.session.get(CameraPoint, camera_id) if camera_id else None
            if cam:
                cam.is_online = True
            session = StreamSession(
                camera_id=camera_id,
                officer_id=current_user.id,
                session_token=secrets.token_urlsafe(12),
                is_active=True,
            )
            db.session.add(session)
            db.session.commit()
            flash("تم بدء جلسة البث المباشر.", "success")
        elif action == "stop" and active:
            active.is_active = False
            active.ended_at = datetime.utcnow()
            if active.camera_id:
                cam = db.session.get(CameraPoint, active.camera_id)
                if cam:
                    others = StreamSession.query.filter_by(camera_id=cam.id, is_active=True).count()
                    if others == 0:
                        cam.is_online = False
            db.session.commit()
            flash("تم إيقاف البث.", "success")
        elif action == "ai":
            camera_id = int(request.form["camera_id"]) if request.form.get("camera_id") else None
            cam = db.session.get(CameraPoint, camera_id) if camera_id else None
            result = simulate_threat(force=True)
            alert = Alert(
                title=f"AI Field: {result['threat_type'].replace('_', ' ').title()}",
                description=result["details"],
                severity=result["severity"],
                confidence=result["confidence"],
                threat_type=result["threat_type"],
                lat=cam.lat if cam else current_user.last_lat,
                lng=cam.lng if cam else current_user.last_lng,
                camera_id=cam.id if cam else None,
                officer_id=current_user.id,
            )
            if cam and result["severity"] in ("high", "critical"):
                cam.zone_status = "red"
            db.session.add(alert)
            db.session.commit()
            flash("تم إرسال تنبيه AI لغرفة العمليات.", "warning")
        return redirect(url_for("main.field_stream"))

    return render_template("field_stream.html", cameras=cameras, active=active)


@main_bp.route("/field/map", methods=["GET", "POST"])
@login_required
@role_required("officer")
def field_map():
    if request.method == "POST":
        try:
            current_user.last_lat = float(request.form.get("lat"))
            current_user.last_lng = float(request.form.get("lng"))
            current_user.last_seen = datetime.utcnow()
            db.session.commit()
            flash("تم تحديث موقعك على الخريطة.", "success")
        except (TypeError, ValueError):
            flash("إحداثيات غير صالحة.", "danger")
        return redirect(url_for("main.field_map"))
    return render_template("field_map.html", **_map_payload())


@main_bp.route("/field/alerts")
@login_required
@role_required("officer")
def field_alerts():
    items = Alert.query.filter(Alert.status.in_(["open", "acknowledged"])).order_by(Alert.created_at.desc()).all()
    return render_template("field_alerts.html", alerts=items)


@main_bp.route("/field/tasks", methods=["GET", "POST"])
@login_required
@role_required("officer")
def field_tasks():
    return tasks()


@main_bp.route("/field/chat", methods=["GET", "POST"])
@login_required
@role_required("officer")
def field_chat():
    return chat()
