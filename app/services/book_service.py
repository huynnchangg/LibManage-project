from sqlalchemy import func

from ..extensions import db
from ..models import (
    COPY_AVAILABLE, COPY_BORROWED, LOAN_BORROWING, LOAN_PENDING, LOAN_READY,
    Book, BookCopy, Category, Loan, User,
)
from .loan_service import LoanError


def search_books(q="", category_id=None, only_available=False, page=1, per_page=9, active_only=True):
    query = Book.query
    if active_only:
        query = query.filter(Book.is_active.is_(True))
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
        raise LoanError("Vui lòng nhập đầy đủ tên sách và tác giả.")

    try:
        total = int(form.get("total_copies", 1))
        year = int(form["year"]) if form.get("year") else None
        price = int(form.get("price", 100000)) if form.get("price") else 100000
    except ValueError:
        raise LoanError("Số lượng bản in, giá bìa và năm xuất bản phải là chữ số hợp lệ.")

    if total < 1:
        raise LoanError("Tổng số lượng bản in phải lớn hơn hoặc bằng 1.")
    if price < 0:
        raise LoanError("Giá bìa sách không hợp lệ.")

    is_new = book.id is None

    book.title = title
    book.author = author
    book.year = year
    book.price = price
    book.isbn = form.get("isbn", "").strip() or None
    book.publisher = form.get("publisher", "").strip() or None
    book.description = form.get("description", "").strip() or None
    book.cover_url = form.get("cover_url", "").strip() or None
    book.location = form.get("location", "").strip() or None
    book.category_id = int(form["category_id"]) if form.get("category_id") else None

    if is_new:
        book.total_copies = total
        book.available_copies = total
        db.session.add(book)
        db.session.flush()

        # Tạo tự động các bản sao BookCopy với mã vạch
        for idx in range(1, total + 1):
            barcode = f"BC{book.id:04d}{idx:02d}"
            copy = BookCopy(
                book_id=book.id,
                barcode=barcode,
                location=book.location,
                status=COPY_AVAILABLE,
                condition="Mới",
            )
            db.session.add(copy)
    else:
        # Chỉnh sửa sách hiện tại: đồng bộ số lượng BookCopy
        current_copies = BookCopy.query.filter_by(book_id=book.id).all()
        current_count = len(current_copies)
        borrowed_count = sum(1 for c in current_copies if c.status in (COPY_BORROWED, "reserved"))

        if total < borrowed_count:
            raise LoanError(f"Hiện có {borrowed_count} bản đang được giữ hoặc mượn. Tổng số bản không thể nhỏ hơn {borrowed_count}.")

        if total > current_count:
            # Bổ sung thêm bản sao mới
            for idx in range(current_count + 1, total + 1):
                barcode = f"BC{book.id:04d}{idx:02d}"
                # Tránh trùng nếu đã từng xóa
                counter = idx
                while BookCopy.query.filter_by(barcode=barcode).first():
                    counter += 1
                    barcode = f"BC{book.id:04d}{counter:02d}"
                copy = BookCopy(
                    book_id=book.id,
                    barcode=barcode,
                    location=book.location,
                    status=COPY_AVAILABLE,
                    condition="Mới",
                )
                db.session.add(copy)
        elif total < current_count:
            # Cần giảm bớt: chỉ giảm các bản sao đang available và chưa từng có mượn
            to_remove = current_count - total
            avail_copies = [c for c in current_copies if c.status == COPY_AVAILABLE and not c.loans]
            if len(avail_copies) < to_remove:
                raise LoanError(f"Không thể giảm số lượng xuống {total} vì các bản sao hiện tại đều đang có dữ liệu ràng buộc.")
            for c in avail_copies[:to_remove]:
                db.session.delete(c)

        db.session.flush()
        book.sync_copies_count()

    db.session.commit()
    return book


def toggle_book_active(book):
    """Ẩn hoặc kích hoạt lại sách phục vụ độc giả."""
    book.is_active = not book.is_active
    db.session.commit()
    return book.is_active


def delete_book(book):
    if book.loans:
        raise LoanError("Ấn bản này đã có lịch sử mượn trả, không thể xoá hoàn toàn khỏi hệ thống (bạn có thể ẩn sách khỏi mục tìm kiếm của độc giả).")
    db.session.delete(book)
    db.session.commit()


def save_category(name):
    name = (name or "").strip()
    if not name:
        raise LoanError("Vui lòng nhập tên thể loại sách (không được để trống).")
    if Category.query.filter_by(name=name).first():
        raise LoanError("Thể loại sách này đã tồn tại trên hệ thống.")
    cat = Category(name=name)
    db.session.add(cat)
    db.session.commit()
    return cat


def update_category(cat, new_name):
    new_name = (new_name or "").strip()
    if not new_name:
        raise LoanError("Tên thể loại sách không được để trống.")
    existing = Category.query.filter_by(name=new_name).first()
    if existing and existing.id != cat.id:
        raise LoanError("Tên thể loại này đã trùng với một thể loại khác trên hệ thống.")
    cat.name = new_name
    db.session.commit()
    return cat


def delete_category(cat):
    if cat.books:
        raise LoanError("Không thể xoá thể loại này vì vẫn còn đầu sách đang thuộc về nó.")
    db.session.delete(cat)
    db.session.commit()


def dashboard_stats():
    unpaid = db.session.query(func.coalesce(func.sum(Loan.fine_amount), 0)).filter(
        Loan.fine_amount > 0, Loan.fine_paid.is_(False)).scalar()

    borrowing = Loan.query.filter_by(status=LOAN_BORROWING).all()
    total_copies = db.session.query(func.coalesce(func.sum(Book.total_copies), 0)).scalar()
    avail_copies = db.session.query(func.coalesce(func.sum(Book.available_copies), 0)).scalar()

    top_books = (db.session.query(Book.title, func.count(Loan.id).label("n"))
                 .join(Loan, Loan.book_id == Book.id)
                 .filter(Loan.status.in_(["borrowing", "returned", "lost", "damaged"]))
                 .group_by(Book.id).order_by(func.count(Loan.id).desc()).limit(5).all())

    by_category = (db.session.query(Category.name, func.count(Loan.id).label("n"))
                   .join(Book, Book.category_id == Category.id)
                   .join(Loan, Loan.book_id == Book.id)
                   .filter(Loan.status.in_(["borrowing", "returned", "lost", "damaged"]))
                   .group_by(Category.id)
                   .order_by(func.count(Loan.id).desc())
                   .limit(5).all())

    top_readers = (db.session.query(User.full_name, func.count(Loan.id).label("n"))
                   .join(Loan, Loan.user_id == User.id).group_by(User.id)
                   .order_by(func.count(Loan.id).desc()).limit(5).all())

    return {
        "total_titles": Book.query.count(),
        "total_copies": total_copies,
        "available_copies": avail_copies,
        "readers": User.query.filter_by(role="reader").count(),
        "pending": Loan.query.filter_by(status=LOAN_PENDING).count(),
        "ready": Loan.query.filter_by(status=LOAN_READY).count(),
        "borrowing": len(borrowing),
        "overdue": sum(1 for l in borrowing if l.is_overdue),
        "unpaid": unpaid,
        "top_books": top_books,
        "by_category": by_category,
        "top_readers": top_readers,
    }


def public_stats():
    """Số liệu hiển thị ở trang chủ (độc giả chưa cần đăng nhập)."""
    return {
        "titles": Book.query.filter(Book.is_active.is_(True)).count(),
        "copies": db.session.query(func.coalesce(func.sum(Book.total_copies), 0)).filter(Book.is_active.is_(True)).scalar(),
        "readers": User.query.filter_by(role="reader").count(),
        "categories": Category.query.count(),
    }
