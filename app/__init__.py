from flask import Flask, jsonify, render_template, request

from .config import Config
from .extensions import csrf, db, login_manager


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from .blueprints import admin, api, auth, main
    for module in (auth, main, admin, api):
        app.register_blueprint(module.bp)

    with app.app_context():
        db.create_all()

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
        return render_template("error.html", code=403, msg="Bạn không có quyền truy cập trang này."), 403

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith("/api/"):
            return jsonify(error="not found"), 404
        return render_template("error.html", code=404, msg="Không tìm thấy trang yêu cầu."), 404

    return app
