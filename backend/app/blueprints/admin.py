"""Chức năng quản trị dành cho thủ thư (RBAC: chỉ role admin)."""
from datetime import date
from functools import wraps

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
import re

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import (
    COPY_AVAILABLE, COPY_BORROWED, COPY_DAMAGED, COPY_LOST, COPY_MAINTENANCE, COPY_RESERVED,
    LOAN_BORROWING, LOAN_CANCELLED, LOAN_DAMAGED, LOAN_LOST, LOAN_PENDING, LOAN_READY, LOAN_REJECTED, LOAN_RETURNED, ROLE_READER,
    Book, BookCopy, Category, Loan, LoanSlip, User,
)
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


@bp.before_request
def admin_before_request():
    """Tự động kiểm tra và hủy các phiếu quá hạn 48h chưa đến nhận khi thủ thư truy cập quản trị."""
    if current_user.is_authenticated and current_user.is_admin:
        loan_service.cancel_expired_pickups()


def _try(action, ok_msg, redirect_to, *args, **kwargs):
    try:
        result = action(*args, **kwargs)
        flash(ok_msg(result) if callable(ok_msg) else ok_msg, "success")
    except LoanError as e:
        flash(str(e), "danger")
    return redirect(redirect_to)


@bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", s=book_service.dashboard_stats())


# ===========================================================================
# SÁCH & BẢN SAO (BOOK & BOOKCOPY)
# ===========================================================================

@bp.route("/books")
@admin_required
def books():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    page = request.args.get("page", 1, type=int)
    pagination = book_service.search_books(
        q=q,
        category_id=category_id,
        page=page,
        per_page=15,
        active_only=False
    )
    return render_template(
        "admin/books.html",
        pagination=pagination,
        categories=Category.query.order_by(Category.name).all(),
        q=q,
        category_id=category_id
    )


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
            flash("Đã lưu thông tin ấn bản và đồng bộ các bản sao thành công.", "success")
            return redirect(url_for("admin.books"))
        except LoanError as e:
            flash(str(e), "danger")
    return render_template(
        "admin/book_form.html",
        book=book,
        categories=Category.query.order_by(Category.name).all()
    )


@bp.route("/books/<int:book_id>/toggle", methods=["POST"])
@admin_required
def book_toggle(book_id):
    book = Book.query.get_or_404(book_id)
    is_active = book_service.toggle_book_active(book)
    flash(f"Đã {'mở lưu hành' if is_active else 'ẩn tạm thời'} cuốn “{book.title}”.", "info")
    return redirect(url_for("admin.books"))


@bp.route("/books/<int:book_id>/copies")
@admin_required
def book_copies(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template("admin/book_copies.html", book=book)


@bp.route("/books/<int:book_id>/copies/<int:copy_id>/edit", methods=["POST"])
@admin_required
def book_copy_edit(book_id, copy_id):
    """Cập nhật trạng thái và tình trạng thực tế của một bản sao vật lý."""
    book = Book.query.get_or_404(book_id)
    copy = BookCopy.query.filter_by(id=copy_id, book_id=book.id).first_or_404()
    new_status = request.form.get("status", "").strip()
    condition = request.form.get("condition", "").strip()
    note = request.form.get("note", "").strip()

    if copy.status in (COPY_BORROWED, COPY_RESERVED) and new_status != copy.status:
        flash(f"Bản sao {copy.barcode} đang trong lượt mượn hoặc giữ chỗ, không thể đổi trạng thái thủ công.", "danger")
        return redirect(url_for("admin.book_copies", book_id=book.id))

    valid_statuses = [COPY_AVAILABLE, COPY_DAMAGED, COPY_LOST, COPY_MAINTENANCE]
    if new_status not in valid_statuses:
        flash("Trạng thái bản sao không hợp lệ.", "danger")
        return redirect(url_for("admin.book_copies", book_id=book.id))

    copy.status = new_status
    if condition:
        copy.condition = condition
    copy.note = note or None

    book.sync_copies_count()
    db.session.commit()

    flash(f"Đã cập nhật trạng thái bản sao {copy.barcode} thành “{copy.status_label[0]}”.", "success")
    return redirect(url_for("admin.book_copies", book_id=book.id))


@bp.route("/books/<int:book_id>/delete", methods=["POST"])
@admin_required
def book_delete(book_id):
    return _try(
        book_service.delete_book,
        "Đã xoá ấn bản thành công khỏi kho tài liệu.",
        url_for("admin.books"),
        Book.query.get_or_404(book_id)
    )


# ===========================================================================
# THỂ LOẠI (CATEGORIES)
# ===========================================================================

@bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        try:
            book_service.save_category(name)
            flash("Đã thêm thể loại sách mới thành công.", "success")
        except LoanError as e:
            flash(str(e), "danger")
        return redirect(url_for("admin.categories"))
    return render_template(
        "admin/categories.html",
        categories=Category.query.order_by(Category.name).all()
    )


@bp.route("/categories/<int:cat_id>/edit", methods=["POST"])
@admin_required
def category_edit(cat_id):
    cat = Category.query.get_or_404(cat_id)
    new_name = request.form.get("name", "").strip()
    try:
        book_service.update_category(cat, new_name)
        flash(f"Đã cập nhật tên thể loại thành “{cat.name}”.", "success")
    except LoanError as e:
        flash(str(e), "danger")
    return redirect(url_for("admin.categories"))


@bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@admin_required
def category_delete(cat_id):
    cat = Category.query.get_or_404(cat_id)
    return _try(
        book_service.delete_category,
        f"Đã xoá thể loại “{cat.name}” thành công.",
        url_for("admin.categories"),
        cat
    )


# ===========================================================================
# QUẢN LÝ ĐỘC GIẢ (USERS)
# ===========================================================================

@bp.route("/users")
@admin_required
def users():
    q = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "all")
    page = request.args.get("page", 1, type=int)

    query = User.query.filter(User.role == ROLE_READER)
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.student_code.ilike(like),
                User.email.ilike(like)
            )
        )
    if status_filter == "active":
        query = query.filter(User.active.is_(True))
    elif status_filter == "locked":
        query = query.filter(User.active.is_(False))

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=12, error_out=False)
    return render_template("admin/users.html", pagination=pagination, users=pagination.items, q=q, status_filter=status_filter)


@bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def user_new():
    if request.method == "POST":
        f = request.form
        username = f.get("username", "").strip()
        email = f.get("email", "").strip().lower()
        full_name = f.get("full_name", "").strip()
        student_code = f.get("student_code", "").strip()
        password = f.get("password", "").strip() or "reader123"

        if not username or not email or not full_name:
            flash("Vui lòng điền đầy đủ tên đăng nhập, email và họ tên.", "danger")
        elif "<" in full_name or ">" in full_name or "<" in username or ">" in username:
            flash("Họ tên và tên đăng nhập không được chứa ký tự HTML (< hoặc >).", "danger")
        elif User.query.filter_by(username=username).first():
            flash("Tên đăng nhập này đã tồn tại trên hệ thống.", "danger")
        elif User.query.filter_by(email=email).first():
            flash("Địa chỉ email này đã được sử dụng.", "danger")
        elif len(password) < 6:
            flash("Mật khẩu phải có tối thiểu 6 ký tự.", "danger")
        else:
            user = User(username=username, email=email, full_name=full_name, student_code=student_code or None, role=ROLE_READER)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash(f"Đã tạo tài khoản độc giả @{user.username} thành công.", "success")
            return redirect(url_for("admin.users"))

    return render_template("admin/user_form.html", user=None)


@bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        abort(403)
    loans = Loan.query.filter_by(user_id=user.id).order_by(Loan.requested_at.desc()).all()
    unpaid = sum(l.fine_amount for l in loans if l.fine_amount and not l.fine_paid)
    return render_template("admin/user_detail.html", user=user, loans=loans, unpaid=unpaid)


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
@admin_required
def user_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        abort(403)
    new_pass = request.form.get("new_password", "").strip()
    if not new_pass or len(new_pass) < 6:
        flash("Mật khẩu mới phải có độ dài tối thiểu 6 ký tự.", "danger")
        return redirect(url_for("admin.user_detail", user_id=user.id))

    user.set_password(new_pass)
    db.session.commit()
    flash(f"Đã đặt lại mật khẩu cho độc giả @{user.username} thành công.", "success")
    return redirect(url_for("admin.user_detail", user_id=user.id))


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def user_toggle(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        abort(403)
    user.active = not user.active
    db.session.commit()
    flash(("Đã mở khoá" if user.active else "Đã khoá") + f" tài khoản độc giả @{user.username} thành công.", "info")
    return redirect(request.referrer or url_for("admin.users"))


# ===========================================================================
# QUẢN LÝ MƯỢN TRẢ (LOANS & SLIPS)
# ===========================================================================

@bp.route("/loans")
@admin_required
def loans():
    status = request.args.get("status", "pending")
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 15

    query = Loan.query.options(joinedload(Loan.user), joinedload(Loan.book), joinedload(Loan.copy), joinedload(Loan.slip))

    if status == "ready":
        query = query.filter(Loan.status == LOAN_READY)
    elif status == "borrowing":
        query = query.filter(Loan.status == LOAN_BORROWING, Loan.due_date >= date.today())
    elif status == "overdue":
        query = query.filter(Loan.status == LOAN_BORROWING, Loan.due_date < date.today())
    elif status == "returned":
        query = query.filter(Loan.status.in_([LOAN_RETURNED, LOAN_DAMAGED, LOAN_LOST]))
    elif status == "rejected":
        query = query.filter(Loan.status == LOAN_REJECTED)
    elif status == "cancelled":
        query = query.filter(Loan.status == LOAN_CANCELLED)
    elif status == "all":
        pass
    else:
        query = query.filter(Loan.status == LOAN_PENDING)

    if q:
        like = f"%{q}%"
        query = query.join(User, Loan.user_id == User.id).join(Book, Loan.book_id == Book.id).outerjoin(BookCopy, Loan.copy_id == BookCopy.id).outerjoin(LoanSlip, Loan.slip_id == LoanSlip.id).filter(
            db.or_(
                LoanSlip.code.ilike(like),
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.student_code.ilike(like),
                Book.title.ilike(like),
                BookCopy.barcode.ilike(like)
            )
        )

    if status == "overdue":
        order_col = Loan.due_date.asc()
    elif status == "ready":
        order_col = Loan.pickup_deadline.asc()
    elif status == "returned":
        order_col = Loan.returned_at.desc()
    else:
        order_col = Loan.requested_at.desc()
    pagination = query.order_by(order_col).paginate(page=page, per_page=per_page, error_out=False)
    return render_template(
        "admin/loans.html",
        pagination=pagination,
        loans=pagination.items,
        status=status,
        q=q
    )


@bp.route("/loans/checkout", methods=["GET", "POST"])
@admin_required
def loan_checkout():
    """Tạo phiếu mượn trực tiếp tại quầy thư viện (Walk-in Checkout)."""
    if request.method == "POST":
        student_query = request.form.get("student_query", "").strip()
        barcodes_text = request.form.get("barcodes", "").strip()
        note = request.form.get("note", "").strip()

        # Tìm user theo student_code hoặc username
        reader = User.query.filter(
            User.role == ROLE_READER,
            db.or_(
                func.lower(User.student_code) == student_query.lower(),
                func.lower(User.username) == student_query.lower()
            )
        ).first()

        if not reader:
            flash(f"Không tìm thấy độc giả có mã sinh viên hoặc tên đăng nhập “{student_query}”.", "danger")
            return render_template("admin/checkout.html", student_query=student_query, barcodes_text=barcodes_text, note=note)

        # Tách danh sách barcode từ textarea hoặc dấu phẩy
        barcodes = [b.strip() for b in re.split(r"[\s,;]+", barcodes_text) if b.strip()]

        try:
            slip = loan_service.direct_checkout(current_user, reader, barcodes, note=note)
            flash(f"Đã lập phiếu mượn #{slip.code} và giao {len(slip.items)} cuốn sách cho độc giả {reader.full_name} thành công!", "success")
            return redirect(url_for("admin.loans", status="borrowing"))
        except LoanError as e:
            flash(str(e), "danger")
            return render_template("admin/checkout.html", student_query=student_query, barcodes_text=barcodes_text, note=note)

    return render_template("admin/checkout.html", student_query="", barcodes_text="", note="")


def _loan(loan_id):
    return Loan.query.get_or_404(loan_id)


@bp.route("/loans/<int:loan_id>/approve", methods=["POST"])
@admin_required
def loan_approve(loan_id):
    barcode = request.form.get("barcode", "").strip() or None
    return _try(
        loan_service.approve,
        "Đã duyệt yêu cầu mượn sách. Sách chuyển sang trạng thái chờ độc giả nhận tại quầy (giữ 48h).",
        request.referrer or url_for("admin.loans", status="pending"),
        _loan(loan_id), current_user, barcode=barcode
    )


@bp.route("/loans/<int:loan_id>/handover", methods=["POST"])
@admin_required
def loan_handover(loan_id):
    return _try(
        loan_service.handover,
        "Đã xác nhận giao sách thành công. Thời hạn mượn 14 ngày bắt đầu được tính.",
        request.referrer or url_for("admin.loans", status="ready"),
        _loan(loan_id), current_user
    )


@bp.route("/loans/<int:loan_id>/reject", methods=["POST"])
@admin_required
def loan_reject(loan_id):
    reason = request.form.get("reason", "").strip()
    return _try(
        loan_service.reject,
        "Đã từ chối yêu cầu mượn sách của độc giả.",
        request.referrer or url_for("admin.loans", status="pending"),
        _loan(loan_id), current_user, reason=reason
    )


@bp.route("/loans/<int:loan_id>/return", methods=["POST"])
@admin_required
def loan_return(loan_id):
    f = request.form
    condition = f.get("condition", "normal")
    damage_percent_raw = f.get("damage_percent", "0")

    try:
        damage_percent = int(damage_percent_raw) if damage_percent_raw not in (None, "") else 0
    except (ValueError, TypeError):
        flash("Tỷ lệ hư hỏng (%) phải là số nguyên từ 0 đến 100.", "danger")
        return redirect(request.referrer or url_for("admin.loans", status="borrowing"))

    if damage_percent < 0 or damage_percent > 100:
        flash("Tỷ lệ hư hỏng (%) phải nằm trong khoảng từ 0% đến 100%.", "danger")
        return redirect(request.referrer or url_for("admin.loans", status="borrowing"))

    pay_now = f.get("pay_now") == "1"
    note = f.get("note", "").strip()

    def msg(fine):
        fine_vnd = f"{fine:,} đ".replace(",", ".")
        if fine == 0:
            return "Đã nhận trả sách vào kho thành công."
        status_txt = " (đã thanh toán ngay tại quầy)" if pay_now else " (đã ghi nhận nợ phạt vào hồ sơ độc giả)"
        return f"Đã xử lý nhận trả sách thành công. Khoản phạt phát sinh: {fine_vnd}{status_txt}."

    loan = _loan(loan_id)
    return _try(
        loan_service.return_book,
        msg,
        request.referrer or url_for("admin.loans", status="borrowing"),
        loan, current_user,
        condition=condition,
        damage_percent=damage_percent,
        pay_now=pay_now,
        note=note
    )


# ===========================================================================
# TIỀN PHẠT (FINES)
# ===========================================================================

@bp.route("/fines")
@admin_required
def fines():
    paid_filter = request.args.get("paid", "all")
    q = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 15

    query = Loan.query.filter(Loan.fine_amount > 0).join(User, Loan.user_id == User.id).join(Book, Loan.book_id == Book.id)

    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                User.username.ilike(like),
                User.full_name.ilike(like),
                User.student_code.ilike(like),
                Book.title.ilike(like)
            )
        )

    if paid_filter == "unpaid":
        query = query.filter(Loan.fine_paid.is_(False))
    elif paid_filter == "paid":
        query = query.filter(Loan.fine_paid.is_(True))

    pagination = query.order_by(Loan.fine_paid.asc(), Loan.returned_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return render_template(
        "admin/fines.html",
        pagination=pagination,
        loans=pagination.items,
        paid_filter=paid_filter,
        q=q
    )


@bp.route("/fines/<int:loan_id>/pay", methods=["POST"])
@admin_required
def fine_pay(loan_id):
    return _try(
        loan_service.pay_fine,
        "Đã xác nhận thu tiền phạt thành công từ độc giả.",
        request.referrer or url_for("admin.fines"),
        _loan(loan_id),
        current_user
    )
