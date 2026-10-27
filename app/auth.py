from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.models import User

auth_bp = Blueprint("auth", __name__)


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash("لا تملك صلاحية الوصول لهذه الصفحة.", "danger")
                if current_user.is_authenticated and current_user.role == "officer":
                    return redirect(url_for("main.field_home"))
                return redirect(url_for("main.dashboard"))
            return fn(*args, **kwargs)

        return wrapper

    return decorator


@auth_bp.route("/")
def home():
    return render_template("home.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.role == "officer":
            return redirect(url_for("main.field_home"))
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.is_active and user.check_password(password):
            login_user(user)
            flash(f"مرحبًا {user.name}", "success")
            if user.role == "officer":
                return redirect(url_for("main.field_home"))
            return redirect(url_for("main.dashboard"))
        flash("بيانات الدخول غير صحيحة.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("تم تسجيل الخروج.", "success")
    return redirect(url_for("auth.home"))
