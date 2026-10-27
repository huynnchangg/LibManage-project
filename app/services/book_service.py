from sqlalchemy import func

from ..extensions import db
from ..models import LOAN_BORROWING, LOAN_PENDING, Book, Category, Loan, User
from .loan_service import LoanError


def search_books(q="", category_id=None, only_available=False, page=1, per_page=9):
    query = Book.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Book.title.ilike(like), Book.author.ilike(like),
                                    Book.isbn.ilike(like)))
    if category_id:
        query = query.filter(Book.category_id == category_id)
    if only_available:
        query = query.filter(Book.available_copies > 0)
    return query.order_by(Book.title).paginate(page=page, per_page=per_page, error_out=False)


def save_book(book, form):
    title = form.get("title", "").strip()
    author = form.get("author", "").strip()
    if not title or not author:
        raise LoanError("Tên sách và tác giả là bắt buộc.")
    try:
        total = int(form.get("total_copies", 1))
        year = int(form["year"]) if form.get("year") else None
    except ValueError:
        raise LoanError("Số lượng và năm xuất bản phải là số.")
    if total < 0:
        raise LoanError("Số lượng không hợp lệ.")
    if book.id:  # sửa: giữ nhất quán số bản sẵn có
        borrowed = book.total_copies - book.available_copies
        if total < borrowed:
            raise LoanError(f"Đang có {borrowed} bản được mượn, tổng số không thể nhỏ hơn.")
        book.available_copies = total - borrowed
    else:
        book.available_copies = total
    book.title, book.author, book.total_copies, book.year = title, author, total, year
    book.isbn = form.get("isbn", "").strip() or None
    book.publisher = form.get("publisher", "").strip() or None
    book.description = form.get("description", "").strip() or None
    book.cover_url = form.get("cover_url", "").strip() or None
    book.location = form.get("location", "").strip() or None
    book.category_id = int(form["category_id"]) if form.get("category_id") else None
    db.session.add(book)
    db.session.commit()


def delete_book(book):
    if book.loans:
        raise LoanError("Sách đã có lịch sử mượn, không thể xoá (hãy đặt số lượng = 0).")
    db.session.delete(book)
    db.session.commit()


def delete_category(cat):
    if cat.books:
        raise LoanError("Thể loại còn sách, không thể xoá.")
    db.session.delete(cat)
    db.session.commit()


def dashboard_stats():
    unpaid = db.session.query(func.coalesce(func.sum(Loan.fine_amount), 0)).filter(
        Loan.fine_amount > 0, Loan.fine_paid.is_(False)).scalar()
    borrowing = Loan.query.filter_by(status=LOAN_BORROWING).all()
    top_books = (db.session.query(Book.title, func.count(Loan.id).label("n"))
                 .join(Loan, Loan.book_id == Book.id)
                 .filter(Loan.status.in_(["borrowing", "returned"]))
                 .group_by(Book.id).order_by(func.count(Loan.id).desc()).limit(5).all())
    by_category = (db.session.query(Category.name, func.count(Loan.id))
                   .join(Book, Book.category_id == Category.id)
                   .join(Loan, Loan.book_id == Book.id)
                   .group_by(Category.id).all())
    top_readers = (db.session.query(User.full_name, func.count(Loan.id).label("n"))
                   .join(Loan, Loan.user_id == User.id).group_by(User.id)
                   .order_by(func.count(Loan.id).desc()).limit(5).all())
    return {
        "total_titles": Book.query.count(),
        "total_copies": db.session.query(func.coalesce(func.sum(Book.total_copies), 0)).scalar(),
        "readers": User.query.filter_by(role="reader").count(),
        "pending": Loan.query.filter_by(status=LOAN_PENDING).count(),
        "borrowing": len(borrowing),
        "overdue": sum(1 for l in borrowing if l.is_overdue),
        "unpaid": unpaid,
        "top_books": top_books, "by_category": by_category, "top_readers": top_readers,
    }


def public_stats():
    """Số liệu hiển thị ở trang chủ (độc giả chưa cần đăng nhập)."""
    return {
        "titles": Book.query.count(),
        "copies": db.session.query(func.coalesce(func.sum(Book.total_copies), 0)).scalar(),
        "readers": User.query.filter_by(role="reader").count(),
        "categories": Category.query.count(),
    }
