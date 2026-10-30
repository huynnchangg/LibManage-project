"""Tầng dữ liệu (Model): các thực thể và quan hệ của hệ thống quản lý thư viện."""
from datetime import date, datetime, timedelta

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

# Roles
ROLE_READER = "reader"
ROLE_ADMIN = "admin"

# Loại phiếu mượn
SLIP_TYPE_ONLINE = "online"   # Độc giả đặt mượn trực tuyến
SLIP_TYPE_DIRECT = "direct"   # Mượn trực tiếp tại quầy

# Trạng thái lượt mượn / phiếu mượn
LOAN_PENDING = "pending"                  # Chờ thủ thư duyệt (đơn online)
LOAN_READY = "ready_for_pickup"           # Đã duyệt, chờ độc giả đến quầy lấy (giữ 48h)
LOAN_BORROWING = "borrowing"              # Đang mượn (đã nhận sách)
LOAN_RETURNED = "returned"                # Đã trả hoàn tất
LOAN_LOST = "lost"                        # Báo mất sách (đền bù 100%)
LOAN_DAMAGED = "damaged"                  # Sách bị hư hỏng (đền bù 25% - 100%)
LOAN_REJECTED = "rejected"                # Bị từ chối duyệt
LOAN_CANCELLED = "cancelled"              # Độc giả huỷ hoặc quá 48h không đến lấy

# Trạng thái bản sách vật lý (BookCopy)
COPY_AVAILABLE = "available"      # Sẵn sàng trên kệ
COPY_RESERVED = "reserved"        # Đang giữ chỗ cho độc giả đến lấy (trong 48h)
COPY_BORROWED = "borrowed"        # Đang được mượn
COPY_LOST = "lost"                # Đã bị mất
COPY_DAMAGED = "damaged"          # Đang hỏng / chờ xử lý
COPY_MAINTENANCE = "maintenance"  # Bảo dưỡng / không cho mượn

COPY_STATUS_LABELS = {
    COPY_AVAILABLE: ("Sẵn sàng", "success"),
    COPY_RESERVED: ("Đang giữ chỗ", "info"),
    COPY_BORROWED: ("Đang cho mượn", "primary"),
    COPY_LOST: ("Đã mất", "danger"),
    COPY_DAMAGED: ("Hư hỏng", "danger"),
    COPY_MAINTENANCE: ("Bảo dưỡng", "secondary"),
}

STATUS_LABELS = {
    LOAN_PENDING: ("Chờ duyệt", "warning"),
    LOAN_READY: ("Chờ lấy sách", "info"),
    LOAN_BORROWING: ("Đang mượn", "primary"),
    LOAN_RETURNED: ("Đã trả", "success"),
    LOAN_LOST: ("Báo mất", "danger"),
    LOAN_DAMAGED: ("Hư hỏng", "danger"),
    LOAN_REJECTED: ("Bị từ chối", "danger"),
    LOAN_CANCELLED: ("Đã huỷ", "secondary"),
}


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    student_code = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_READER)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    loans = db.relationship("Loan", foreign_keys="Loan.user_id", back_populates="user")
    loan_slips = db.relationship("LoanSlip", foreign_keys="LoanSlip.user_id", back_populates="user")
    cart_items = db.relationship("CartItem", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_active(self):
        return self.active

    @property
    def is_admin(self):
        return self.role == ROLE_ADMIN

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    books = db.relationship("Book", back_populates="category")


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    author = db.Column(db.String(120), nullable=False)
    isbn = db.Column(db.String(20))
    publisher = db.Column(db.String(120))
    year = db.Column(db.Integer)
    description = db.Column(db.Text)
    cover_url = db.Column(db.String(500))          # URL ảnh bìa
    location = db.Column(db.String(50))            # Vị trí kệ, vd: "Kệ CNTT - Ngăn 03"
    price = db.Column(db.Integer, nullable=False, default=100000) # Giá bìa sách (dùng tính tiền đền bù/phạt)
    is_active = db.Column(db.Boolean, nullable=False, default=True) # Còn lưu hành không
    total_copies = db.Column(db.Integer, nullable=False, default=1)
    available_copies = db.Column(db.Integer, nullable=False, default=1)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))

    category = db.relationship("Category", back_populates="books")
    copies = db.relationship("BookCopy", back_populates="book", cascade="all, delete-orphan")
    loans = db.relationship("Loan", back_populates="book")
    cart_items = db.relationship("CartItem", back_populates="book", cascade="all, delete-orphan")

    def sync_copies_count(self):
        """Đồng bộ số lượng tồn kho theo danh sách bản sao vật lý."""
        self.total_copies = len(self.copies)
        self.available_copies = sum(1 for c in self.copies if c.status == COPY_AVAILABLE)

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "author": self.author,
            "isbn": self.isbn, "publisher": self.publisher, "year": self.year,
            "category": self.category.name if self.category else None,
            "cover_url": self.cover_url,
            "location": self.location,
            "price": self.price,
            "total_copies": self.total_copies,
            "available_copies": self.available_copies,
        }


class BookCopy(db.Model):
    """Bản sách vật lý cụ thể – có mã vạch (Barcode) riêng, vị trí và trạng thái cá biệt."""
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False, index=True)
    barcode = db.Column(db.String(40), unique=True, nullable=False, index=True) # vd: "BC100234"
    location = db.Column(db.String(50))                                         # vd: "Kệ 02 - Ngăn 04"
    status = db.Column(db.String(20), nullable=False, default=COPY_AVAILABLE, index=True)
    condition = db.Column(db.String(50), default="Tốt")                         # "Mới", "Tốt", "Cũ", "Rách bìa"...
    note = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)

    book = db.relationship("Book", back_populates="copies")
    loans = db.relationship("Loan", back_populates="copy")

    @property
    def status_label(self):
        return COPY_STATUS_LABELS.get(self.status, (self.status, "secondary"))


class LoanSlip(db.Model):
    """Phiếu mượn sách – gom một hoặc nhiều cuốn sách mượn cùng một đợt."""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False, index=True) # Mã phiếu: "PM-20261028-0001"
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    slip_type = db.Column(db.String(20), nullable=False, default=SLIP_TYPE_ONLINE) # online / direct
    status = db.Column(db.String(20), nullable=False, default=LOAN_PENDING, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    approved_at = db.Column(db.DateTime)
    pickup_deadline = db.Column(db.DateTime)    # Hạn nhận sách (48h sau approved_at)
    borrowed_at = db.Column(db.DateTime)        # Lúc nhận sách thực tế
    due_date = db.Column(db.Date)               # Hạn trả (14 ngày sau borrowed_at)
    completed_at = db.Column(db.DateTime)
    processed_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    note = db.Column(db.String(255))

    user = db.relationship("User", foreign_keys=[user_id], back_populates="loan_slips")
    processor = db.relationship("User", foreign_keys=[processed_by])
    items = db.relationship("Loan", back_populates="slip", cascade="all, delete-orphan")

    @property
    def is_pickup_expired(self):
        """Quá hạn 48h nhận sách tại quầy."""
        return self.status == LOAN_READY and self.pickup_deadline and datetime.now() > self.pickup_deadline

    @property
    def is_overdue(self):
        return any(item.is_overdue for item in self.items)

    @property
    def total_fine(self):
        return sum(item.current_fine for item in self.items)

    @property
    def status_label(self):
        if self.is_pickup_expired:
            return ("Quá hạn lấy sách", "danger")
        if self.is_overdue:
            return ("Quá hạn trả", "danger")
        return STATUS_LABELS.get(self.status, (self.status, "secondary"))


class Loan(db.Model):
    """Một mục mượn trong phiếu – liên kết User, Book, BookCopy và tiền phạt."""
    id = db.Column(db.Integer, primary_key=True)
    slip_id = db.Column(db.Integer, db.ForeignKey("loan_slip.id"), nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False, index=True)
    copy_id = db.Column(db.Integer, db.ForeignKey("book_copy.id"), nullable=True, index=True)
    status = db.Column(db.String(20), nullable=False, default=LOAN_PENDING, index=True)
    requested_at = db.Column(db.DateTime, default=datetime.now)
    approved_at = db.Column(db.DateTime)
    pickup_deadline = db.Column(db.DateTime)
    borrowed_at = db.Column(db.DateTime)
    due_date = db.Column(db.Date)
    returned_at = db.Column(db.DateTime)
    renew_count = db.Column(db.Integer, default=0)

    # Tiền phạt và bồi thường
    fine_overdue = db.Column(db.Integer, default=0)  # Phạt quá hạn
    fine_damage = db.Column(db.Integer, default=0)   # Phạt hư hỏng / mất sách
    damage_percent = db.Column(db.Integer, default=0)# 0%, 25%, 50%, 75%, 100%
    fine_amount = db.Column(db.Integer, default=0)   # Tổng tiền phạt = overdue + damage
    fine_paid = db.Column(db.Boolean, default=False)
    note = db.Column(db.String(255))
    processed_by = db.Column(db.Integer, db.ForeignKey("user.id"))

    slip = db.relationship("LoanSlip", back_populates="items")
    user = db.relationship("User", foreign_keys=[user_id], back_populates="loans")
    book = db.relationship("Book", back_populates="loans")
    copy = db.relationship("BookCopy", back_populates="loans")
    processor = db.relationship("User", foreign_keys=[processed_by])

    @property
    def is_pickup_expired(self):
        return self.status == LOAN_READY and self.pickup_deadline and datetime.now() > self.pickup_deadline

    @property
    def is_overdue(self):
        return self.status == LOAN_BORROWING and self.due_date and date.today() > self.due_date

    @property
    def overdue_days(self):
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

    @property
    def current_fine(self):
        """Tiền phạt hiện tại: đã chốt nếu đã trả/xử lý, tạm tính nếu đang quá hạn."""
        if self.status in (LOAN_RETURNED, LOAN_LOST, LOAN_DAMAGED):
            return self.fine_amount or 0
        return self.overdue_days * current_app.config.get("FINE_PER_DAY", 5000)

    @property
    def status_label(self):
        if self.is_pickup_expired:
            return ("Quá hạn lấy", "danger")
        if self.is_overdue:
            return ("Quá hạn", "danger")
        return STATUS_LABELS.get(self.status, (self.status, "secondary"))


LoanItem = Loan  # Alias cho rõ ngữ cảnh Item trong Slip


class CartItem(db.Model):
    """Giỏ mượn sách tạm thời của độc giả trước khi gửi yêu cầu phiếu mượn."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship("User", back_populates="cart_items")
    book = db.relationship("Book", back_populates="cart_items")
