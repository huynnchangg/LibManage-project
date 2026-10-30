"""REST API (JSON) – dùng cho tích hợp / tra cứu từ ứng dụng khác."""
from flask import Blueprint, abort, jsonify, request
from flask_login import current_user

from ..models import Book
from ..services import book_service

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.route("/books")
def list_books():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 10, type=int), 50)
    p = book_service.search_books(q=request.args.get("q", "").strip(),
                                  category_id=request.args.get("category", type=int),
                                  only_available=request.args.get("available") == "1",
                                  page=page, per_page=per_page)
    return jsonify({"items": [b.to_dict() for b in p.items], "page": p.page,
                    "pages": p.pages, "total": p.total})


@bp.route("/books/<int:book_id>")
def get_book(book_id):
    return jsonify(Book.query.get_or_404(book_id).to_dict())


@bp.route("/stats")
def stats():
    if not (current_user.is_authenticated and current_user.is_admin):
        abort(403)
    s = book_service.dashboard_stats()
    return jsonify({k: s[k] for k in ("total_titles", "total_copies", "readers",
                                      "pending", "borrowing", "overdue", "unpaid")})
