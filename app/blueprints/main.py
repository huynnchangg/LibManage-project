"""Chức năng dành cho độc giả."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..models import Book, Category, Loan
from ..services import book_service, loan_service
from ..services.loan_service import LoanError

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    pagination = book_service.search_books(
        q=request.args.get("q", "").strip(),
        category_id=request.args.get("category", type=int),
        only_available=request.args.get("available") == "1",
        page=page, per_page=current_app.config["PER_PAGE"])
    return render_template("index.html", pagination=pagination,
                           categories=Category.query.order_by(Category.name).all(),
                           stats=book_service.public_stats())


@bp.route("/books/<int:book_id>")
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template("book_detail.html", book=book)


@bp.route("/books/<int:book_id>/borrow", methods=["POST"])
@login_required
def borrow(book_id):
    if current_user.is_admin:
        abort(403)
    book = Book.query.get_or_404(book_id)
    try:
        loan_service.request_loan(current_user, book)
        flash("Đã gửi yêu cầu mượn sách thành công. Vui lòng chờ thủ thư xét duyệt.", "success")
    except LoanError as e:
        flash(str(e), "danger")
    return redirect(url_for("main.my_loans"))


@bp.route("/my/loans")
@login_required
def my_loans():
    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.requested_at.desc()).all()
    return render_template("my_loans.html", loans=loans,
                           unpaid=loan_service.unpaid_fines(current_user))


def _own_loan(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.user_id != current_user.id:
        abort(403)
    return loan


@bp.route("/my/loans/<int:loan_id>/cancel", methods=["POST"])
@login_required
def cancel(loan_id):
    try:
        loan_service.cancel_request(_own_loan(loan_id), current_user)
        flash("Yêu cầu mượn sách đã được huỷ thành công.", "info")
    except LoanError as e:
        flash(str(e), "danger")
    return redirect(url_for("main.my_loans"))


@bp.route("/my/loans/<int:loan_id>/renew", methods=["POST"])
@login_required
def renew(loan_id):
    try:
        loan_service.renew(_own_loan(loan_id), current_user)
        flash("Gia hạn thời gian mượn sách thành công!", "success")
    except LoanError as e:
        flash(str(e), "danger")
    return redirect(url_for("main.my_loans"))
