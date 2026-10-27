"""Tầng nghiệp vụ (Service): toàn bộ quy tắc mượn – trả – phạt nằm ở đây.
Controller chỉ gọi hàm, không tự xử lý logic."""
from datetime import date, datetime, timedelta

from flask import current_app

from ..extensions import db
from ..models import (LOAN_BORROWING, LOAN_CANCELLED, LOAN_PENDING, LOAN_REJECTED,
                      LOAN_RETURNED, Loan)


class LoanError(Exception):
    """Lỗi nghiệp vụ, thông điệp hiển thị trực tiếp cho người dùng."""


def _cfg(key):
    return current_app.config[key]


def unpaid_fines(user):
    """Tổng tiền phạt chưa nộp (đã chốt) của độc giả."""
    loans = Loan.query.filter(Loan.user_id == user.id, Loan.fine_amount > 0,
                              Loan.fine_paid.is_(False)).all()
    return sum(l.fine_amount for l in loans)


def active_loans(user):
    return Loan.query.filter(Loan.user_id == user.id,
                             Loan.status.in_([LOAN_PENDING, LOAN_BORROWING])).all()


def request_loan(user, book):
    if not user.active:
        raise LoanError("Tài khoản của bạn đang bị khoá.")
    if unpaid_fines(user) > 0:
        raise LoanError("Bạn còn tiền phạt chưa nộp, vui lòng thanh toán tại quầy thủ thư.")
    current = active_loans(user)
    if any(l.is_overdue for l in current):
        raise LoanError("Bạn đang có sách quá hạn, hãy trả sách trước khi mượn thêm.")
    if len(current) >= _cfg("MAX_ACTIVE_LOANS"):
        raise LoanError(f"Bạn chỉ được mượn/đặt tối đa {_cfg('MAX_ACTIVE_LOANS')} cuốn cùng lúc.")
    if any(l.book_id == book.id for l in current):
        raise LoanError("Bạn đã mượn hoặc đã gửi yêu cầu mượn cuốn sách này.")
    if book.available_copies < 1:
        raise LoanError("Sách hiện đã hết bản, vui lòng quay lại sau.")
    loan = Loan(user_id=user.id, book_id=book.id, status=LOAN_PENDING)
    db.session.add(loan)
    db.session.commit()
    return loan


def cancel_request(loan, user):
    if loan.user_id != user.id:
        raise LoanError("Bạn không có quyền với yêu cầu này.")
    if loan.status != LOAN_PENDING:
        raise LoanError("Chỉ huỷ được yêu cầu đang chờ duyệt.")
    loan.status = LOAN_CANCELLED
    db.session.commit()


def approve(loan, admin):
    if loan.status != LOAN_PENDING:
        raise LoanError("Yêu cầu này không còn ở trạng thái chờ duyệt.")
    book = loan.book
    if book.available_copies < 1:
        raise LoanError(f"Sách '{book.title}' đã hết bản, không thể duyệt.")
    book.available_copies -= 1
    loan.status = LOAN_BORROWING
    loan.approved_at = datetime.now()
    loan.due_date = date.today() + timedelta(days=_cfg("LOAN_DAYS"))
    loan.processed_by = admin.id
    db.session.commit()


def reject(loan, admin, reason=""):
    if loan.status != LOAN_PENDING:
        raise LoanError("Yêu cầu này không còn ở trạng thái chờ duyệt.")
    loan.status = LOAN_REJECTED
    loan.note = (reason or "")[:255] or None
    loan.processed_by = admin.id
    db.session.commit()


def return_book(loan, admin):
    if loan.status != LOAN_BORROWING:
        raise LoanError("Lượt mượn này không ở trạng thái đang mượn.")
    fine = loan.overdue_days * _cfg("FINE_PER_DAY")
    loan.status = LOAN_RETURNED
    loan.returned_at = datetime.now()
    loan.fine_amount = fine
    loan.fine_paid = fine == 0
    loan.processed_by = admin.id
    loan.book.available_copies = min(loan.book.total_copies, loan.book.available_copies + 1)
    db.session.commit()
    return fine


def renew(loan, user):
    if loan.user_id != user.id:
        raise LoanError("Bạn không có quyền với lượt mượn này.")
    if not user.active:
        raise LoanError("Tài khoản của bạn đang bị khoá.")
    if unpaid_fines(user) > 0:
        raise LoanError("Bạn còn tiền phạt chưa nộp, vui lòng thanh toán tại quầy thủ thư.")
    if loan.status != LOAN_BORROWING:
        raise LoanError("Chỉ gia hạn được sách đang mượn.")
    if loan.is_overdue:
        raise LoanError("Sách đã quá hạn, không thể gia hạn.")
    if loan.renew_count >= _cfg("MAX_RENEWALS"):
        raise LoanError("Bạn đã dùng hết số lần gia hạn.")
    loan.due_date += timedelta(days=_cfg("RENEW_DAYS"))
    loan.renew_count += 1
    db.session.commit()


def pay_fine(loan):
    if not loan.fine_amount or loan.fine_paid:
        raise LoanError("Lượt mượn này không có khoản phạt cần thu.")
    loan.fine_paid = True
    db.session.commit()
