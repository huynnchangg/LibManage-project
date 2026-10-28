"""Tầng nghiệp vụ (Service): toàn bộ quy tắc mượn – trả – phạt nằm ở đây.
Controller chỉ gọi hàm, không tự xử lý logic."""
from datetime import date, datetime, timedelta

from flask import current_app

from ..extensions import db
from ..models import (
    COPY_AVAILABLE, COPY_BORROWED, COPY_DAMAGED, COPY_LOST, COPY_RESERVED,
    LOAN_BORROWING, LOAN_CANCELLED, LOAN_DAMAGED, LOAN_LOST, LOAN_PENDING,
    LOAN_READY, LOAN_REJECTED, LOAN_RETURNED, SLIP_TYPE_DIRECT, SLIP_TYPE_ONLINE,
    Book, BookCopy, CartItem, Loan, LoanSlip, User,
)


class LoanError(Exception):
    """Lỗi nghiệp vụ, thông điệp hiển thị trực tiếp cho người dùng."""


def _cfg(key, default=None):
    return current_app.config.get(key, default)


def generate_slip_code():
    """Tạo mã phiếu mượn dạng PM-YYYYMM-XXXX."""
    prefix = f"PM-{datetime.now().strftime('%Y%m')}"
    last_slip = LoanSlip.query.filter(LoanSlip.code.like(f"{prefix}-%")).order_by(LoanSlip.id.desc()).first()
    if last_slip:
        try:
            seq = int(last_slip.code.split("-")[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}-{seq:04d}"


def unpaid_fines(user):
    """Tổng tiền phạt chưa nộp (đã chốt) của độc giả."""
    loans = Loan.query.filter(
        Loan.user_id == user.id,
        Loan.fine_amount > 0,
        Loan.fine_paid.is_(False)
    ).all()
    return sum(l.fine_amount for l in loans)


def active_loans(user):
    """Danh sách các cuốn sách đang trong luồng mượn chưa kết thúc."""
    return Loan.query.filter(
        Loan.user_id == user.id,
        Loan.status.in_([LOAN_PENDING, LOAN_READY, LOAN_BORROWING])
    ).all()


def validate_user_eligibility(user, additional_count=1):
    """Kiểm tra điều kiện để độc giả được mượn thêm sách."""
    if not user.active:
        raise LoanError("Tài khoản độc giả của bạn hiện đang bị khóa. Vui lòng liên hệ thủ thư để được hỗ trợ.")
    if unpaid_fines(user) > 0:
        raise LoanError("Bạn còn khoản tiền phạt chưa thanh toán. Vui lòng nộp phạt tại quầy thư viện trước khi mượn tiếp.")
    current = active_loans(user)
    if any(l.is_overdue for l in current):
        raise LoanError("Bạn đang có sách mượn quá hạn chưa trả. Vui lòng mang sách trả lại thư viện trước khi mượn mới.")
    max_loans = _cfg("MAX_ACTIVE_LOANS", 5)
    if len(current) + additional_count > max_loans:
        raise LoanError(f"Mỗi độc giả chỉ được mượn hoặc giữ chỗ tối đa {max_loans} cuốn sách cùng lúc (hiện bạn đang có {len(current)} cuốn).")


# ===========================================================================
# GIỎ MƯỢN SÁCH (BORROW CART)
# ===========================================================================

def get_cart_items(user):
    return CartItem.query.filter_by(user_id=user.id).all()


def add_to_cart(user, book):
    validate_user_eligibility(user, additional_count=0)
    current = active_loans(user)
    if any(l.book_id == book.id for l in current):
        raise LoanError(f"Bạn hiện đang mượn hoặc đã gửi yêu cầu cho cuốn “{book.title}”.")
    existing = CartItem.query.filter_by(user_id=user.id, book_id=book.id).first()
    if existing:
        raise LoanError(f"Cuốn “{book.title}” đã có sẵn trong danh sách mượn của bạn.")
    cart_count = CartItem.query.filter_by(user_id=user.id).count()
    max_loans = _cfg("MAX_ACTIVE_LOANS", 5)
    if len(current) + cart_count + 1 > max_loans:
        raise LoanError(f"Số sách trong giỏ cộng với số sách đang mượn vượt quá giới hạn tối đa ({max_loans} cuốn).")
    if book.available_copies < 1:
        raise LoanError(f"Ấn bản “{book.title}” hiện tạm thời hết bản in sẵn có trong kho.")

    item = CartItem(user_id=user.id, book_id=book.id)
    db.session.add(item)
    db.session.commit()
    return item


def remove_from_cart(user, book_id):
    item = CartItem.query.filter_by(user_id=user.id, book_id=book_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()


def clear_cart(user):
    CartItem.query.filter_by(user_id=user.id).delete()
    db.session.commit()


def checkout_cart(user, note=""):
    """Tạo một Phiếu mượn (LoanSlip) gom tất cả sách trong giỏ mượn."""
    items = get_cart_items(user)
    if not items:
        raise LoanError("Giỏ mượn sách của bạn đang trống.")

    validate_user_eligibility(user, additional_count=len(items))

    for it in items:
        if it.book.available_copies < 1:
            raise LoanError(f"Ấn bản “{it.book.title}” vừa hết bản in sẵn sàng. Vui lòng xóa khỏi giỏ hoặc quay lại sau.")

    slip = LoanSlip(
        code=generate_slip_code(),
        user_id=user.id,
        slip_type=SLIP_TYPE_ONLINE,
        status=LOAN_PENDING,
        note=(note or "").strip()[:255] or None,
    )
    db.session.add(slip)
    db.session.flush()

    for it in items:
        loan = Loan(
            slip_id=slip.id,
            user_id=user.id,
            book_id=it.book_id,
            status=LOAN_PENDING,
            requested_at=slip.created_at,
        )
        db.session.add(loan)
        db.session.delete(it)

    db.session.commit()
    return slip


# ===========================================================================
# MƯỢN TRỰC TUYẾN 1-CLICK (SINGLE FAST BORROW)
# ===========================================================================

def request_loan(user, book):
    """Độc giả gửi yêu cầu mượn 1 cuốn sách (tương thích backward và mượn nhanh 1-click)."""
    validate_user_eligibility(user, additional_count=1)
    current = active_loans(user)
    if any(l.book_id == book.id for l in current):
        raise LoanError("Bạn hiện đã mượn hoặc đã gửi yêu cầu mượn cuốn sách này.")
    if book.available_copies < 1:
        raise LoanError("Ấn bản này hiện tạm thời hết bản in sẵn có trong kho. Vui lòng quay lại sau.")

    slip = LoanSlip(
        code=generate_slip_code(),
        user_id=user.id,
        slip_type=SLIP_TYPE_ONLINE,
        status=LOAN_PENDING,
    )
    db.session.add(slip)
    db.session.flush()

    loan = Loan(
        slip_id=slip.id,
        user_id=user.id,
        book_id=book.id,
        status=LOAN_PENDING,
        requested_at=slip.created_at,
    )
    db.session.add(loan)
    db.session.commit()
    return loan


def cancel_request(loan, user):
    """Huỷ yêu cầu mượn khi đang ở trạng thái pending hoặc ready."""
    if loan.user_id != user.id:
        raise LoanError("Bạn không có quyền thao tác trên yêu cầu mượn sách này.")
    if loan.status not in (LOAN_PENDING, LOAN_READY):
        raise LoanError("Chỉ có thể huỷ những yêu cầu mượn đang chờ duyệt hoặc đang chờ lấy sách.")

    if loan.copy and loan.copy.status == COPY_RESERVED:
        loan.copy.status = COPY_AVAILABLE
        loan.book.available_copies = min(loan.book.total_copies, loan.book.available_copies + 1)
        loan.copy_id = None

    loan.status = LOAN_CANCELLED
    if loan.slip:
        all_cancelled = all(item.status == LOAN_CANCELLED for item in loan.slip.items if item.id != loan.id)
        if all_cancelled:
            loan.slip.status = LOAN_CANCELLED

    db.session.commit()


# ===========================================================================
# QUY TRÌNH THỦ THƯ TẠI QUẦY (DUYỆT - GIAO - MƯỢN TRỰC TIẾP - TRẢ - PHẠT)
# ===========================================================================

def approve(loan, admin, barcode=None):
    """Thủ thư DUYỆT yêu cầu online:
    Gán bản sách BookCopy cụ thể, chuyển sang trạng thái READY_FOR_PICKUP (chờ lấy trong 48h).
    """
    if loan.status != LOAN_PENDING:
        raise LoanError("Yêu cầu mượn này không còn ở trạng thái chờ duyệt.")

    book = loan.book
    copy = None
    if barcode:
        copy = BookCopy.query.filter_by(barcode=barcode.strip(), book_id=book.id).first()
        if not copy:
            raise LoanError(f"Mã vạch {barcode} không thuộc đầu sách này.")
        if copy.status != COPY_AVAILABLE:
            raise LoanError(f"Bản sao mã vạch {barcode} hiện không ở trạng thái sẵn sàng cho mượn.")
    else:
        copy = BookCopy.query.filter_by(book_id=book.id, status=COPY_AVAILABLE).first()

    if not copy or book.available_copies < 1:
        raise LoanError(f"Sách “{book.title}” hiện đã hết bản in sẵn sàng trong kho, không thể duyệt cho mượn.")

    copy.status = COPY_RESERVED
    book.available_copies = max(0, book.available_copies - 1)

    now = datetime.now()
    pickup_hrs = _cfg("PICKUP_HOURS", 48)
    deadline = now + timedelta(hours=pickup_hrs)

    loan.copy_id = copy.id
    loan.status = LOAN_READY
    loan.approved_at = now
    loan.pickup_deadline = deadline
    loan.processed_by = admin.id

    if loan.slip:
        loan.slip.status = LOAN_READY
        loan.slip.approved_at = now
        loan.slip.pickup_deadline = deadline
        loan.slip.processed_by = admin.id

    db.session.commit()


def handover(loan, admin):
    """Xác nhận sinh viên đã đến quầy nhận sách:
    Chuyển trạng thái sang BORROWING và bắt đầu đếm hạn trả 14 ngày.
    """
    if loan.status != LOAN_READY:
        raise LoanError("Lượt mượn này không ở trạng thái chờ lấy sách.")

    if not loan.copy:
        raise LoanError("Chưa có bản sách cụ thể nào được gán cho lượt mượn này.")

    now = datetime.now()
    loan_days = _cfg("LOAN_DAYS", 14)
    due = date.today() + timedelta(days=loan_days)

    loan.copy.status = COPY_BORROWED
    loan.status = LOAN_BORROWING
    loan.borrowed_at = now
    loan.due_date = due
    loan.processed_by = admin.id

    if loan.slip:
        loan.slip.status = LOAN_BORROWING
        loan.slip.borrowed_at = now
        loan.slip.due_date = due
        loan.slip.processed_by = admin.id

    db.session.commit()


def direct_checkout(admin, user, barcodes, note=""):
    """Thủ thư tạo phiếu mượn trực tiếp tại quầy cho sinh viên (Walk-in Checkout)."""
    if not barcodes:
        raise LoanError("Vui lòng nhập ít nhất một mã vạch sách cần mượn.")

    clean_barcodes = list(dict.fromkeys([b.strip() for b in barcodes if b.strip()]))
    if not clean_barcodes:
        raise LoanError("Danh sách mã vạch không hợp lệ.")

    validate_user_eligibility(user, additional_count=len(clean_barcodes))

    copies = []
    for code in clean_barcodes:
        cp = BookCopy.query.filter_by(barcode=code).first()
        if not cp:
            raise LoanError(f"Không tìm thấy bản sách có mã vạch “{code}” trong hệ thống.")
        if cp.status != COPY_AVAILABLE:
            raise LoanError(f"Bản sách “{code}” ({cp.book.title}) hiện không khả dụng (trạng thái: {cp.status_label[0]}).")
        copies.append(cp)

    now = datetime.now()
    due = date.today() + timedelta(days=_cfg("LOAN_DAYS", 14))

    slip = LoanSlip(
        code=generate_slip_code(),
        user_id=user.id,
        slip_type=SLIP_TYPE_DIRECT,
        status=LOAN_BORROWING,
        created_at=now,
        approved_at=now,
        borrowed_at=now,
        due_date=due,
        processed_by=admin.id,
        note=(note or "").strip()[:255] or None,
    )
    db.session.add(slip)
    db.session.flush()

    for cp in copies:
        cp.status = COPY_BORROWED
        cp.book.available_copies = max(0, cp.book.available_copies - 1)
        loan = Loan(
            slip_id=slip.id,
            user_id=user.id,
            book_id=cp.book_id,
            copy_id=cp.id,
            status=LOAN_BORROWING,
            requested_at=now,
            approved_at=now,
            borrowed_at=now,
            due_date=due,
            processed_by=admin.id,
        )
        db.session.add(loan)

    db.session.commit()
    return slip


def reject(loan, admin, reason=""):
    """Từ chối yêu cầu mượn."""
    if loan.status != LOAN_PENDING:
        raise LoanError("Yêu cầu mượn này không còn ở trạng thái chờ duyệt.")

    if loan.copy and loan.copy.status == COPY_RESERVED:
        loan.copy.status = COPY_AVAILABLE
        loan.book.available_copies = min(loan.book.total_copies, loan.book.available_copies + 1)
        loan.copy_id = None

    loan.status = LOAN_REJECTED
    loan.note = (reason or "")[:255] or None
    loan.processed_by = admin.id

    if loan.slip:
        all_rejected = all(item.status in (LOAN_REJECTED, LOAN_CANCELLED) for item in loan.slip.items if item.id != loan.id)
        if all_rejected:
            loan.slip.status = LOAN_REJECTED
            loan.slip.note = loan.note
            loan.slip.processed_by = admin.id

    db.session.commit()


def return_book(loan, admin, condition="normal", damage_percent=0, pay_now=False, note=""):
    """Xử lý trả sách tại quầy:
    - condition: 'normal' | 'damaged' | 'lost'
    - damage_percent: 0, 25, 50, 75, 100 (% giá bìa sách)
    - pay_now: Độc giả thanh toán tiền phạt ngay tại quầy
    """
    if loan.status != LOAN_BORROWING:
        raise LoanError("Lượt mượn này hiện không ở trạng thái đang mượn, không thể nhận trả.")

    now = datetime.now()
    overdue_fine = loan.overdue_days * _cfg("FINE_PER_DAY", 5000)
    damage_fine = 0
    dmg_pct = int(damage_percent or 0)

    book = loan.book
    copy = loan.copy

    if condition == "lost" or dmg_pct >= 100:
        loan.status = LOAN_LOST
        dmg_pct = 100
        damage_fine = book.price
        if copy:
            copy.status = COPY_LOST
            copy.condition = "Đã báo mất"
    elif condition == "damaged" or dmg_pct > 0:
        loan.status = LOAN_DAMAGED
        damage_fine = int(book.price * (dmg_pct / 100.0))
        if copy:
            copy.status = COPY_DAMAGED
            copy.condition = f"Hư hỏng {dmg_pct}%: {(note or '').strip()}"
    else:
        loan.status = LOAN_RETURNED
        if copy:
            copy.status = COPY_AVAILABLE
            copy.condition = "Tốt"
        book.available_copies = min(book.total_copies, book.available_copies + 1)

    total_fine = overdue_fine + damage_fine
    loan.fine_overdue = overdue_fine
    loan.fine_damage = damage_fine
    loan.damage_percent = dmg_pct
    loan.fine_amount = total_fine
    loan.fine_paid = (total_fine == 0) or bool(pay_now)
    loan.returned_at = now
    loan.processed_by = admin.id
    if note:
        loan.note = (note or "").strip()[:255]

    if loan.slip:
        active_items = [i for i in loan.slip.items if i.id != loan.id and i.status == LOAN_BORROWING]
        if not active_items:
            loan.slip.status = LOAN_RETURNED
            loan.slip.completed_at = now

    db.session.commit()
    return total_fine


def renew(loan, user):
    """Gia hạn thời gian mượn sách."""
    if loan.user_id != user.id:
        raise LoanError("Bạn không có quyền thao tác trên lượt mượn này.")
    if not user.active:
        raise LoanError("Tài khoản độc giả của bạn hiện đang bị khóa. Vui lòng liên hệ thủ thư để được hỗ trợ.")
    if unpaid_fines(user) > 0:
        raise LoanError("Bạn còn tiền phạt chưa nộp, vui lòng thanh toán tại quầy thư viện trước khi gia hạn.")
    if loan.status != LOAN_BORROWING:
        raise LoanError("Chỉ có thể gia hạn đối với những cuốn sách đang trong thời hạn mượn.")
    if loan.is_overdue:
        raise LoanError("Sách đã quá hạn quy định nên không thể gia hạn. Vui lòng mang sách hoàn trả tại quầy thư viện.")
    max_renewals = _cfg("MAX_RENEWALS", 1)
    if loan.renew_count >= max_renewals:
        raise LoanError(f"Bạn đã sử dụng hết số lần gia hạn cho phép ({max_renewals} lần) đối với cuốn sách này.")

    renew_days = _cfg("RENEW_DAYS", 7)
    loan.due_date += timedelta(days=renew_days)
    loan.renew_count += 1
    if loan.slip:
        loan.slip.due_date = loan.due_date
    db.session.commit()


def pay_fine(loan):
    """Xác nhận thu tiền phạt từ độc giả."""
    if not loan.fine_amount or loan.fine_paid:
        raise LoanError("Lượt mượn này không có khoản tiền phạt nào cần ghi nhận thu.")
    loan.fine_paid = True
    db.session.commit()
