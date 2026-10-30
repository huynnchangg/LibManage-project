"""Chức năng dành cho độc giả: tra cứu, giỏ mượn, mượn sách, lịch sử."""
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..models import Book, Category, Loan, LoanSlip
from ..services import book_service, loan_service
from ..services.loan_service import LoanError

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    category_id = request.args.get("category", type=int)
    only_available = request.args.get("available") == "1"
    q = request.args.get("q", "").strip()

    pagination = book_service.search_books(
        q=q,
        category_id=category_id,
        only_available=only_available,
        page=page,
        per_page=current_app.config["PER_PAGE"]
    )
    return render_template(
        "index.html",
        pagination=pagination,
        categories=Category.query.order_by(Category.name).all(),
        stats=book_service.public_stats(),
        selected_cat=category_id,
        q=q,
        only_available=only_available,
    )


@bp.route("/books/<int:book_id>")
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template("book_detail.html", book=book)


# ===========================================================================
# MƯỢN TRỰC TUYẾN 1-CLICK & GIỎ MƯỢN
# ===========================================================================

@bp.route("/books/<int:book_id>/borrow", methods=["POST"])
@login_required
def borrow(book_id):
    if current_user.is_admin:
        abort(403)
    book = Book.query.get_or_404(book_id)
    try:
        loan = loan_service.request_loan(current_user, book)
        flash(f"Đã tạo phiếu mượn #{loan.slip.code if loan.slip else loan.id} cho cuốn “{book.title}”. Vui lòng chờ thủ thư xét duyệt.", "success")
    except LoanError as e:
        flash(str(e), "danger")
    return redirect(url_for("main.my_loans"))


@bp.route("/cart")
@login_required
def cart():
    if current_user.is_admin:
        abort(403)
    items = loan_service.get_cart_items(current_user)
    return render_template("cart.html", items=items, unpaid=loan_service.unpaid_fines(current_user))


@bp.route("/cart/add/<int:book_id>", methods=["POST"])
@login_required
def cart_add(book_id):
    if current_user.is_admin:
        abort(403)
    book = Book.query.get_or_404(book_id)
    try:
        loan_service.add_to_cart(current_user, book)
        flash(f"Đã thêm cuốn “{book.title}” vào danh sách giỏ mượn.", "success")
    except LoanError as e:
        flash(str(e), "danger")
    return redirect(request.referrer or url_for("main.cart"))


@bp.route("/cart/remove/<int:book_id>", methods=["POST"])
@login_required
def cart_remove(book_id):
    if current_user.is_admin:
        abort(403)
    loan_service.remove_from_cart(current_user, book_id)
    flash("Đã bỏ cuốn sách khỏi danh sách giỏ mượn.", "info")
    return redirect(url_for("main.cart"))


@bp.route("/cart/clear", methods=["POST"])
@login_required
def cart_clear():
    if current_user.is_admin:
        abort(403)
    loan_service.clear_cart(current_user)
    flash("Đã xóa toàn bộ sách trong giỏ mượn.", "info")
    return redirect(url_for("main.cart"))


@bp.route("/cart/checkout", methods=["POST"])
@login_required
def cart_checkout():
    if current_user.is_admin:
        abort(403)
    note = request.form.get("note", "").strip()
    try:
        slip = loan_service.checkout_cart(current_user, note=note)
        flash(f"Đã gửi phiếu mượn #{slip.code} gồm {len(slip.items)} cuốn thành công! Vui lòng chờ thủ thư xét duyệt.", "success")
        return redirect(url_for("main.my_loans"))
    except LoanError as e:
        flash(str(e), "danger")
        return redirect(url_for("main.cart"))


# ===========================================================================
# TRANG SÁCH CỦA TÔI & LỊCH SỬ PHIẾU MƯỢN
# ===========================================================================

@bp.route("/my/loans")
@login_required
def my_loans():
    loans = Loan.query.filter_by(user_id=current_user.id).order_by(Loan.requested_at.desc()).all()
    slips = LoanSlip.query.filter_by(user_id=current_user.id).order_by(LoanSlip.created_at.desc()).all()
    return render_template(
        "my_loans.html",
        loans=loans,
        slips=slips,
        unpaid=loan_service.unpaid_fines(current_user)
    )


@bp.route("/my/slips/<int:slip_id>")
@login_required
def slip_detail(slip_id):
    slip = LoanSlip.query.get_or_404(slip_id)
    if slip.user_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template("slip_detail.html", slip=slip)


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
        flash("Gia hạn thời gian mượn sách thành công (+7 ngày)!", "success")
    except LoanError as e:
        flash(str(e), "danger")
    return redirect(url_for("main.my_loans"))
