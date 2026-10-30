import os
from flask import Flask, jsonify, render_template, request
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.engine import Engine

from .config import Config
from .extensions import csrf, db, login_manager


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Kích hoạt ràng buộc khóa ngoại (Foreign Key Constraints) cho SQLite."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
    finally:
        cursor.close()


def create_app(config_object=Config):
    # Tự động xác định đường dẫn thư mục frontend và backend instance
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    root_dir = os.path.abspath(os.path.join(backend_dir, ".."))
    frontend_dir = os.path.join(root_dir, "frontend")
    template_dir = os.path.join(frontend_dir, "templates")
    static_dir = os.path.join(frontend_dir, "static")
    instance_dir = os.path.join(backend_dir, "instance")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
        instance_path=instance_dir
    )
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .blueprints import admin, api, auth, main
    for module in (auth, main, admin, api):
        app.register_blueprint(module.bp)

    with app.app_context():
        db.create_all()

    from .models import CartItem

    @app.context_processor
    def inject_cart():
        count = 0
        if current_user.is_authenticated and not current_user.is_admin:
            try:
                count = CartItem.query.filter_by(user_id=current_user.id).count()
            except Exception:
                count = 0
        return {"cart_count": count}

    @app.template_filter("vnd")
    def vnd(value):
        return f"{int(value or 0):,} đ".replace(",", ".")

    @app.template_filter("dt")
    def dt(value, fmt="%d/%m/%Y %H:%M"):
        return value.strftime(fmt) if value else "—"

    @app.after_request
    def security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/"):
            return jsonify(error="forbidden"), 403
        return render_template("error.html", code=403, msg="Bạn không có quyền truy cập vào tài nguyên hoặc khu vực này."), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify(error="not found"), 404
        return render_template("error.html", code=404, msg="Trang hoặc tài liệu bạn đang tìm kiếm không tồn tại hoặc đã được di chuyển."), 404

    return app
