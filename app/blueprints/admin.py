"""Chức năng quản trị dành cho thủ thư (RBAC: chỉ role admin)."""
from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import LOAN_BORROWING, Book, Category, Loan, User
from ..services import book_service, loan_service
from ..services.loan_service import LoanError

bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*a, **kw):
        if not current_user.is_admin:
            abort(403)
        return fn(*a, **kw)
    return wrapper


def _try(action, ok_msg, redirect_to, *args):
    try:
        result = action(*args)
        flash(ok_msg(result) if callable(ok_msg) else ok_msg, "success")
    except LoanError as e:
        flash(str(e), "danger")
    return redirect(redirect_to)


@bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", s=book_service.dashboard_stats())


# ---------- Sách ----------
@bp.route("/books")
@admin_required
def books():
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    pagination = book_service.search_books(q=q, page=page, per_page=15)
    return render_template("admin/books.html", pagination=pagination)


@bp.route("/books/new", methods=["GET", "POST"])
@admin_required
def book_new():
    return _book_form(Book())


@bp.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
@admin_required
def book_edit(book_id):
    return _book_form(Book.query.get_or_404(book_id))


def _book_form(book):
    if request.method == "POST":
        try:
            book_service.save_book(book, request.form)
            flash("Đã lưu sách.", "success")
            return redirect(url_for("admin.books"))
        except LoanError as e:
            flash(str(e), "danger")
    return render_template("admin/book_form.html", book=book,
                           categories=Category.query.order_by(Category.name).all())


@bp.route("/books/<int:book_id>/delete", methods=["POST"])
@admin_required
def book_delete(book_id):
    return _try(book_service.delete_book, "Đã xoá sách.", url_for("admin.books"),
                Book.query.get_or_404(book_id))


# ---------- Thể loại ----------
@bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Tên thể loại không được trống.", "danger")
        elif Category.query.filter_by(name=name).first():
            flash("Thể loại đã tồn tại.", "danger")
        else:
            db.session.add(Category(name=name))
            db.session.commit()
            flash("Đã thêm thể loại.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/categories.html",
                           categories=Category.query.order_by(Category.name).all())


@bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def category_delete(cat_id):
    return _try(book_service.delete_category, "Đã xoá thể loại.", url_for("admin.categories"),
                Category.query.get_or_404(cat_id))


# ---------- Độc giả ----------
@bp.route("/users")
@admin_required
def users():
    q = request.args.get("q", "").strip()
    query = User.query.filter_by(role="reader")
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.full_name.ilike(like), User.username.ilike(like),
                                     User.student_code.ilike(like)))
    return render_template("admin/users.html", users=query.order_by(User.full_name).all())


@bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        abort(403)
    loans = Loan.query.filter_by(user_id=user.id).order_by(Loan.requested_at.desc()).all()
    unpaid = sum(l.fine_amount for l in loans if l.fine_amount and not l.fine_paid)
    return render_template("admin/user_detail.html", user=user, loans=loans, unpaid=unpaid)


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def user_toggle(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        abort(403)
    user.active = not user.active
    db.session.commit()
    flash(("Đã mở khoá" if user.active else "Đã khoá") + f" tài khoản {user.username}.", "info")
    return redirect(url_for("admin.users"))


# ---------- Mượn trả ----------
@bp.route("/loans")
@admin_required
def loans():
    status = request.args.get("status", "pending")
    page = request.args.get("page", 1, type=int)
    per_page = 15

    query = Loan.query
    if status == "overdue":
        query = query.filter(Loan.status == LOAN_BORROWING, Loan.due_date < date.today()).order_by(Loan.due_date.asc())
    else:
        if status != "all":
            query = query.filter_by(status=status)
        query = query.order_by(Loan.requested_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return render_template("admin/loans.html", pagination=pagination, loans=pagination.items, status=status)


def _loan(loan_id):
    return Loan.query.get_or_404(loan_id)


@bp.route("/loans/<int:loan_id>/approve", methods=["POST"])
@admin_required
def loan_approve(loan_id):
    return _try(loan_service.approve, "Đã duyệt yêu cầu, bắt đầu tính hạn trả.",
                url_for("admin.loans", status="pending"), _loan(loan_id), current_user)


@bp.route("/loans/<int:loan_id>/reject", methods=["POST"])
@admin_required
def loan_reject(loan_id):
    return _try(loan_service.reject, "Đã từ chối yêu cầu.",
                url_for("admin.loans", status="pending"), _loan(loan_id), current_user,
                request.form.get("reason", ""))


@bp.route("/loans/<int:loan_id>/return", methods=["POST"])
@admin_required
def loan_return(loan_id):
    def msg(fine):
        return "Đã nhận trả sách." if not fine else f"Đã nhận trả sách. Phạt quá hạn: {fine:,} đ."
    return _try(loan_service.return_book, msg, url_for("admin.loans", status="borrowing"),
                _loan(loan_id), current_user)


# ---------- Tiền phạt ----------
@bp.route("/fines")
@admin_required
def fines():
    items = Loan.query.filter(Loan.fine_amount > 0).order_by(Loan.fine_paid, Loan.returned_at.desc()).all()
    return render_template("admin/fines.html", loans=items)


@bp.route("/fines/<int:loan_id>/pay", methods=["POST"])
@admin_required
def fine_pay(loan_id):
    return _try(loan_service.pay_fine, "Đã ghi nhận thu tiền phạt.", url_for("admin.fines"),
                _loan(loan_id))
