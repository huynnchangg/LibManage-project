"""Khởi tạo DB đầy đủ: schema, categories, users, sách và loan mẫu.

Chạy lệnh để khởi tạo:
    python seed.py --reset    # xóa toàn bộ và tạo mới từ đầu với dữ liệu phong phú
    python seed.py            # thêm nếu chưa có (idempotent)
"""
import io
import json
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# Force UTF-8 trên Windows console
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from app import create_app
from app.extensions import db
from app.models import (
    LOAN_BORROWING, LOAN_CANCELLED, LOAN_PENDING, LOAN_REJECTED, LOAN_RETURNED,
    Book, Category, Loan, ROLE_ADMIN, ROLE_READER, User,
)

# ---------------------------------------------------------------------------
# Dữ liệu mẫu
# ---------------------------------------------------------------------------

ADMIN_USER = dict(
    username="admin",
    email="admin@library.vn",
    full_name="Thủ thư Admin",
    password="admin123",
)

# 18 độc giả mẫu sinh động với đầy đủ khoa viện trường ĐH
SAMPLE_READERS = [
    dict(username="reader01", email="reader01@neu.edu.vn", full_name="Nguyễn Văn An", student_code="11210001", password="reader123"),
    dict(username="reader02", email="reader02@neu.edu.vn", full_name="Trần Thị Bình", student_code="11210002", password="reader123"),
    dict(username="reader03", email="reader03@neu.edu.vn", full_name="Lê Hoàng Nam", student_code="11210003", password="reader123"),
    dict(username="reader04", email="reader04@neu.edu.vn", full_name="Phạm Minh Châu", student_code="11210004", password="reader123"),
    dict(username="reader05", email="reader05@neu.edu.vn", full_name="Đỗ Quỳnh Anh", student_code="11210005", password="reader123"),
    dict(username="reader06", email="reader06@neu.edu.vn", full_name="Vũ Đức Thắng", student_code="11210006", password="reader123"),
    dict(username="reader07", email="reader07@neu.edu.vn", full_name="Hoàng Khánh Linh", student_code="11210007", password="reader123"),
    dict(username="reader08", email="reader08@neu.edu.vn", full_name="Bùi Tuấn Kiệt", student_code="11210008", password="reader123"),
    dict(username="reader09", email="reader09@neu.edu.vn", full_name="Ngô Mai Phương", student_code="11210009", password="reader123"),
    dict(username="reader10", email="reader10@neu.edu.vn", full_name="Đặng Tiến Đạt", student_code="11210010", password="reader123"),
    dict(username="reader11", email="reader11@neu.edu.vn", full_name="Dương Thu Trang", student_code="11210011", password="reader123"),
    dict(username="reader12", email="reader12@neu.edu.vn", full_name="Phan Hải Yến", student_code="11210012", password="reader123"),
    dict(username="reader13", email="reader13@neu.edu.vn", full_name="Trịnh Công Vinh", student_code="11210013", password="reader123"),
    dict(username="reader14", email="reader14@neu.edu.vn", full_name="Lâm Mỹ Duyên", student_code="11210014", password="reader123"),
    dict(username="reader15", email="reader15@neu.edu.vn", full_name="Cao Bá Quát", student_code="11210015", password="reader123"),
    dict(username="reader16", email="reader16@neu.edu.vn", full_name="Đinh Trọng Hưng", student_code="11210016", password="reader123"),
    dict(username="reader17", email="reader17@neu.edu.vn", full_name="Nguyễn Phương Linh", student_code="11210017", password="reader123"),
    dict(username="reader18", email="reader18@neu.edu.vn", full_name="Tạ Đình Phong", student_code="11210018", password="reader123"),
]

DEFAULT_CATEGORIES = [
    "Văn học & Hư cấu",
    "Khoa học & Toán học",
    "Công nghệ & Lập trình",
    "Kinh tế & Kinh doanh",
    "Lịch sử & Xã hội",
    "Sức khỏe & Đời sống",
    "Kỹ năng & Phát triển",
    "Nghệ thuật & Âm nhạc",
    "Thiếu nhi",
    "Giáo khoa",
]

BOOKS_JSON = Path("books_clean.json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_user(data: dict, role: str) -> tuple[User, bool]:
    u = User.query.filter_by(username=data["username"]).first()
    if u:
        return u, False
    u = User(
        username=data["username"],
        email=data["email"],
        full_name=data["full_name"],
        student_code=data.get("student_code"),
        role=role,
    )
    u.set_password(data["password"])
    db.session.add(u)
    db.session.flush()
    return u, True


def _seed_categories() -> dict[str, Category]:
    cache: dict[str, Category] = {}
    added = 0
    for name in DEFAULT_CATEGORIES:
        cat = Category.query.filter_by(name=name).first()
        if not cat:
            cat = Category(name=name)
            db.session.add(cat)
            db.session.flush()
            added += 1
        cache[name] = cat
    if added:
        print(f"✓ Thêm {added} thể loại mới.")
    else:
        print("– Thể loại đã đủ, bỏ qua.")
    return cache


def _seed_books(cat_cache: dict[str, Category]) -> list[Book]:
    """Đọc books_clean.json và thêm sách vào DB với số bản random 1-10."""
    if not BOOKS_JSON.exists():
        print(f"⚠ Không tìm thấy {BOOKS_JSON}. Chạy 'python clean_csv.py' trước.")
        return []

    with open(BOOKS_JSON, encoding="utf-8") as f:
        records = json.load(f)

    added = skipped = 0
    books_added: list[Book] = []

    # Sử dụng seed random cố định để mỗi lần seed đều ra cùng phân bổ
    rnd = random.Random(101)

    for rec in records:
        existing = None
        if rec.get("isbn"):
            existing = Book.query.filter_by(isbn=rec["isbn"]).first()
        if not existing:
            existing = Book.query.filter_by(
                title=rec["title"], author=rec["author"]
            ).first()

        if existing:
            skipped += 1
            continue

        cat_name = rec.get("category", "Văn học & Hư cấu")
        cat = cat_cache.get(cat_name)
        if not cat:
            cat = Category(name=cat_name)
            db.session.add(cat)
            db.session.flush()
            cat_cache[cat_name] = cat

        # Random số bản từ 1 đến 10 cuốn
        total_copies = rnd.randint(1, 10)
        available_copies = total_copies

        book = Book(
            title=rec["title"],
            author=rec["author"],
            isbn=rec.get("isbn"),
            publisher=rec.get("publisher"),
            year=rec.get("year"),
            description=rec.get("description"),
            cover_url=rec.get("cover_url"),
            location=rec.get("location"),
            total_copies=total_copies,
            available_copies=available_copies,
            category_id=cat.id,
        )
        db.session.add(book)
        books_added.append(book)
        added += 1

        if added % 100 == 0:
            db.session.flush()
            print(f"  ... đã thêm {added} cuốn")

    db.session.flush()
    print(f"✓ Sách: thêm {added} cuốn, bỏ qua {skipped} (đã tồn tại).")
    return books_added


def _seed_loans(readers: list[User], books: list[Book], admin: User) -> None:
    """Tạo các lượt mượn trả mẫu sinh động: đang mượn, quá hạn, chờ duyệt, nợ phạt chưa thu."""
    if not books:
        books = Book.query.all()
    if not books or not readers:
        return

    rnd = random.Random(2026)
    today = date.today()
    now = datetime.now()

    pool = books[:min(len(books), 100)]
    loan_records = []
    book_idx = 0

    def next_book():
        nonlocal book_idx
        b = pool[book_idx % len(pool)]
        book_idx += 1
        return b

    # 1. Các lượt mượn bình thường (hạn còn xa, hạn còn gần)
    for reader in readers[:10]:
        b = next_book()
        if b.available_copies > 0:
            b.available_copies -= 1
            loan_records.append(Loan(
                user_id=reader.id,
                book_id=b.id,
                status=LOAN_BORROWING,
                requested_at=now - timedelta(days=rnd.randint(2, 6)),
                approved_at=now - timedelta(days=rnd.randint(1, 2)),
                due_date=today + timedelta(days=rnd.randint(4, 12)),
                processed_by=admin.id,
            ))

    # 2. Các lượt mượn đã QUÁ HẠN (để demo cờ đỏ quá hạn, tính tiền phạt tạm tính)
    for reader in readers[3:8]:
        b = next_book()
        if b.available_copies > 0:
            b.available_copies -= 1
            overdue_days = rnd.randint(2, 14)
            loan_records.append(Loan(
                user_id=reader.id,
                book_id=b.id,
                status=LOAN_BORROWING,
                requested_at=now - timedelta(days=22),
                approved_at=now - timedelta(days=20),
                due_date=today - timedelta(days=overdue_days),
                processed_by=admin.id,
            ))

    # 3. Các lượt đã trả nhưng CHƯA THU TIỀN PHẠT (fine_paid=False) -> để Admin demo thu tiền tại /admin/fines
    for reader in readers[8:13]:
        b = next_book()
        borrow_days = rnd.randint(16, 22)
        overdue_d = borrow_days - 14
        fine = overdue_d * 5000
        loan_records.append(Loan(
            user_id=reader.id,
            book_id=b.id,
            status=LOAN_RETURNED,
            requested_at=now - timedelta(days=borrow_days + 4),
            approved_at=now - timedelta(days=borrow_days + 2),
            due_date=today - timedelta(days=overdue_d),
            returned_at=now - timedelta(days=rnd.randint(1, 3)),
            fine_amount=fine,
            fine_paid=False,  # Chưa nộp phạt
            processed_by=admin.id,
        ))

    # 4. Các lượt đã trả đúng hạn hoặc đã nộp phạt đủ
    for reader in readers[5:15]:
        b = next_book()
        borrow_days = rnd.randint(5, 12)
        loan_records.append(Loan(
            user_id=reader.id,
            book_id=b.id,
            status=LOAN_RETURNED,
            requested_at=now - timedelta(days=borrow_days + 3),
            approved_at=now - timedelta(days=borrow_days + 1),
            due_date=today + timedelta(days=5),
            returned_at=now - timedelta(days=rnd.randint(1, 4)),
            fine_amount=0,
            fine_paid=True,
            processed_by=admin.id,
        ))

    # 5. Các yêu cầu CHỜ DUYỆT (pending) -> để Admin demo duyệt/từ chối tại /admin/loans
    for reader in readers[12:18]:
        b = next_book()
        loan_records.append(Loan(
            user_id=reader.id,
            book_id=b.id,
            status=LOAN_PENDING,
            requested_at=now - timedelta(hours=rnd.randint(2, 36)),
        ))

    # 6. Các yêu cầu BỊ TỪ CHỐI (rejected)
    rejection_reasons = [
        "Sách đang trong đợt bảo quản định kỳ.",
        "Đầu sách này tạm thời chỉ phục vụ đọc tại chỗ.",
        "Thông tin thẻ độc giả cần đối chiếu lại tại quầy.",
    ]
    for i, reader in enumerate(readers[1:4]):
        b = next_book()
        loan_records.append(Loan(
            user_id=reader.id,
            book_id=b.id,
            status=LOAN_REJECTED,
            requested_at=now - timedelta(days=rnd.randint(3, 7)),
            note=rejection_reasons[i % len(rejection_reasons)],
            processed_by=admin.id,
        ))

    # 7. Các yêu cầu ĐÃ HUỶ (cancelled) do độc giả
    for reader in readers[6:9]:
        b = next_book()
        loan_records.append(Loan(
            user_id=reader.id,
            book_id=b.id,
            status=LOAN_CANCELLED,
            requested_at=now - timedelta(days=rnd.randint(1, 4)),
        ))

    for loan in loan_records:
        db.session.add(loan)

    db.session.flush()
    print(f"✓ Tạo {len(loan_records)} loan records mẫu đa dạng.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    reset = "--reset" in sys.argv
    app = create_app()

    with app.app_context():
        if reset:
            print("⚠️ Reset: xóa toàn bộ DB...")
            db.drop_all()
            print("   Xong.\n")

        db.create_all()

        # 1. Categories
        cat_cache = _seed_categories()

        # 2. Admin
        admin, created = _get_or_create_user(ADMIN_USER, ROLE_ADMIN)
        if created:
            print(f"✓ Tạo admin: {ADMIN_USER['username']} / {ADMIN_USER['password']}")
        else:
            print(f"– Admin '{ADMIN_USER['username']}' đã tồn tại.")

        # 3. Readers mẫu (18 độc giả)
        readers = []
        new_readers = 0
        for data in SAMPLE_READERS:
            u, created = _get_or_create_user(data, ROLE_READER)
            readers.append(u)
            if created:
                new_readers += 1
        if new_readers:
            print(f"✓ Tạo {new_readers} độc giả mẫu sinh viên NEU (mật khẩu: reader123).")
        else:
            print(f"– {len(readers)} độc giả mẫu đã tồn tại.")

        # 4. Sách
        books = _seed_books(cat_cache)

        # 5. Loans mẫu
        if reset or Loan.query.count() == 0:
            _seed_loans(readers, books if books else Book.query.all(), admin)

        db.session.commit()

        print("\n" + "="*50)
        print("✅ Seed hoàn tất CSDL thành công!")
        print(f"   Admin  : {ADMIN_USER['username']} / {ADMIN_USER['password']}")
        print(f"   Reader : reader01..18 / reader123")
        print("="*50)


if __name__ == "__main__":
    main()
