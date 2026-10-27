from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import ROLE_READER, User

bp = Blueprint("auth", __name__)


def _safe_next(target):
    # chỉ chấp nhận đường dẫn nội bộ để tránh open-redirect
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and user.check_password(request.form.get("password", "")):
            if not user.active:
                flash("Tài khoản đã bị khoá, liên hệ thủ thư.", "danger")
            else:
                login_user(user)
                default = "admin.dashboard" if user.is_admin else "main.index"
                return redirect(_safe_next(request.args.get("next")) or url_for(default))
        else:
            flash("Sai tên đăng nhập hoặc mật khẩu.", "danger")
    return render_template("login.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        f = request.form
        username, email = f.get("username", "").strip(), f.get("email", "").strip().lower()
        full_name, password = f.get("full_name", "").strip(), f.get("password", "")
        error = None
        if not (username and email and full_name):
            error = "Vui lòng điền đủ thông tin bắt buộc."
        elif len(password) < 6:
            error = "Mật khẩu tối thiểu 6 ký tự."
        elif len(password) > 128:
            error = "Mật khẩu tối đa 128 ký tự."
        elif password != f.get("confirm", ""):
            error = "Mật khẩu nhập lại không khớp."
        elif User.query.filter((User.username == username) | (User.email == email)).first():
            error = "Tên đăng nhập hoặc email đã tồn tại."
        if error:
            flash(error, "danger")
        else:
            user = User(username=username, email=email, full_name=full_name,
                        student_code=f.get("student_code", "").strip() or None, role=ROLE_READER)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash("Đăng ký thành công, hãy đăng nhập.", "success")
            return redirect(url_for("auth.login"))
    return render_template("register.html")


@bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        f = request.form
        old_password = f.get("old_password", "")
        new_password = f.get("new_password", "")
        confirm = f.get("confirm", "")

        error = None
        if not (old_password and new_password and confirm):
            error = "Vui lòng điền đầy đủ các thông tin."
        elif not current_user.check_password(old_password):
            error = "Mật khẩu hiện tại không đúng."
        elif len(new_password) < 6:
            error = "Mật khẩu mới tối thiểu 6 ký tự."
        elif len(new_password) > 128:
            error = "Mật khẩu mới tối đa 128 ký tự."
        elif new_password != confirm:
            error = "Mật khẩu xác nhận không khớp."
        elif old_password == new_password:
            error = "Mật khẩu mới không được trùng mật khẩu cũ."

        if error:
            flash(error, "danger")
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash("Đổi mật khẩu thành công.", "success")
            default = "admin.dashboard" if current_user.is_admin else "main.index"
            return redirect(url_for(default))

    return render_template("change_password.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Đã đăng xuất.", "info")
    return redirect(url_for("main.index"))
