"""Tầng dữ liệu (Model): các thực thể và quan hệ của hệ thống."""
from datetime import date, datetime

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

ROLE_READER = "reader"
ROLE_ADMIN = "admin"

LOAN_PENDING = "pending"      # chờ thủ thư duyệt
LOAN_BORROWING = "borrowing"  # đang mượn
LOAN_RETURNED = "returned"    # đã trả
LOAN_REJECTED = "rejected"    # bị từ chối
LOAN_CANCELLED = "cancelled"  # độc giả tự huỷ

STATUS_LABELS = {
    LOAN_PENDING: ("Chờ duyệt", "warning"),
    LOAN_BORROWING: ("Đang mượn", "primary"),
    LOAN_RETURNED: ("Đã trả", "success"),
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

    @property
    def is_active(self):  # Flask-Login: tài khoản bị khoá không đăng nhập được
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
    total_copies = db.Column(db.Integer, nullable=False, default=1)
    available_copies = db.Column(db.Integer, nullable=False, default=1)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"))

    category = db.relationship("Category", back_populates="books")
    loans = db.relationship("Loan", back_populates="book")

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "author": self.author,
            "isbn": self.isbn, "publisher": self.publisher, "year": self.year,
            "category": self.category.name if self.category else None,
            "total_copies": self.total_copies,
            "available_copies": self.available_copies,
        }


class Loan(db.Model):
    """Một lượt mượn sách – thực thể trung tâm liên kết User, Book và tiền phạt."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=LOAN_PENDING, index=True)
    requested_at = db.Column(db.DateTime, default=datetime.now)
    approved_at = db.Column(db.DateTime)
    due_date = db.Column(db.Date)
    returned_at = db.Column(db.DateTime)
    renew_count = db.Column(db.Integer, default=0)
    fine_amount = db.Column(db.Integer, default=0)
    fine_paid = db.Column(db.Boolean, default=False)
    note = db.Column(db.String(255))
    processed_by = db.Column(db.Integer, db.ForeignKey("user.id"))

    user = db.relationship("User", foreign_keys=[user_id], back_populates="loans")
    book = db.relationship("Book", back_populates="loans")
    processor = db.relationship("User", foreign_keys=[processed_by])

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
        """Tiền phạt hiện tại: đã chốt nếu đã trả, tạm tính nếu đang quá hạn."""
        if self.status == LOAN_RETURNED:
            return self.fine_amount or 0
        return self.overdue_days * current_app.config["FINE_PER_DAY"]

    @property
    def status_label(self):
        if self.is_overdue:
            return ("Quá hạn", "danger")
        return STATUS_LABELS.get(self.status, (self.status, "secondary"))
