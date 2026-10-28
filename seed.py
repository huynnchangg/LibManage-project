"""Khởi tạo DB đầy đủ: schema, categories, users, sách, bản sao (BookCopy) và phiếu mượn (LoanSlip) mẫu.

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
    COPY_AVAILABLE, COPY_BORROWED, COPY_DAMAGED, COPY_LOST, COPY_RESERVED,
    LOAN_BORROWING, LOAN_CANCELLED, LOAN_DAMAGED, LOAN_LOST, LOAN_PENDING,
    LOAN_READY, LOAN_REJECTED, LOAN_RETURNED, ROLE_ADMIN, ROLE_READER,
    SLIP_TYPE_DIRECT, SLIP_TYPE_ONLINE,
    Book, BookCopy, Category, Loan, LoanSlip, User,
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
    """Đọc books_clean.json, thêm sách và tự động tạo các bản sách BookCopy với barcode cá biệt."""
    if not BOOKS_JSON.exists():
        print(f"⚠ Không tìm thấy {BOOKS_JSON}.")
        return []

    with open(BOOKS_JSON, encoding="utf-8") as f:
        records = json.load(f)

    added = skipped = 0
    books_added: list[Book] = []
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

        total_copies = rnd.randint(2, 6)
        # Giá bìa ngẫu nhiên từ 60.000đ đến 250.000đ làm tròn đến 5.000đ
        price = rnd.randint(12, 50) * 5000

        book = Book(
            title=rec["title"],
            author=rec["author"],
            isbn=rec.get("isbn"),
            publisher=rec.get("publisher"),
            year=rec.get("year"),
            description=rec.get("description"),
            cover_url=rec.get("cover_url"),
            location=rec.get("location") or f"Kệ {rnd.choice(['A','B','C','D'])}{rnd.randint(1,5)} - Ngăn {rnd.randint(1,6):02d}",
            price=price,
            is_active=True,
            total_copies=total_copies,
            available_copies=total_copies,
            category_id=cat.id,
        )
        db.session.add(book)
        db.session.flush()

        # Tạo từng bản sao BookCopy với Barcode riêng biệt
        for c_idx in range(1, total_copies + 1):
            barcode = f"BC{book.id:04d}{c_idx:02d}"
            copy = BookCopy(
                book_id=book.id,
                barcode=barcode,
                location=book.location,
                status=COPY_AVAILABLE,
                condition=rnd.choice(["Mới", "Tốt", "Tốt", "Khá"]),
            )
            db.session.add(copy)

        books_added.append(book)
        added += 1

        if added % 100 == 0:
            db.session.flush()
            print(f"  ... đã thêm {added} đầu sách và các bản sao vật lý")

    db.session.flush()
    print(f"✓ Sách: thêm {added} cuốn, bỏ qua {skipped} (đã tồn tại).")
    return books_added


def _seed_loans(readers: list[User], books: list[Book], admin: User) -> None:
    """Tạo các phiếu mượn (LoanSlip) và chi tiết lượt mượn (Loan/LoanItem) mẫu chuẩn thực tế."""
    if not books:
        books = Book.query.all()
    if not books or not readers:
        return

    rnd = random.Random(2026)
    today = date.today()
    now = datetime.now()

    pool = books[:min(len(books), 100)]
    slip_counter = 1

    def make_slip_code():
        nonlocal slip_counter
        code = f"PM-{now.strftime('%Y%m')}-{slip_counter:04d}"
        slip_counter += 1
        return code

    # Helper lấy 1 copy available của sách
    def get_available_copy(book: Book):
        for cp in book.copies:
            if cp.status == COPY_AVAILABLE:
                return cp
        return None

    # 1. Các lượt mượn bình thường (đang mượn, còn hạn)
    for reader in readers[:6]:
        book = pool[slip_counter % len(pool)]
        copy = get_available_copy(book)
        if not copy:
            continue
        copy.status = COPY_BORROWED
        book.available_copies = max(0, book.available_copies - 1)

        slip = LoanSlip(
            code=make_slip_code(),
            user_id=reader.id,
            slip_type=SLIP_TYPE_ONLINE,
            status=LOAN_BORROWING,
            created_at=now - timedelta(days=rnd.randint(3, 7)),
            approved_at=now - timedelta(days=rnd.randint(2, 5)),
            pickup_deadline=now - timedelta(days=rnd.randint(1, 3)),
            borrowed_at=now - timedelta(days=rnd.randint(1, 4)),
            due_date=today + timedelta(days=rnd.randint(5, 12)),
            processed_by=admin.id,
        )
        db.session.add(slip)
        db.session.flush()

        loan = Loan(
            slip_id=slip.id,
            user_id=reader.id,
            book_id=book.id,
            copy_id=copy.id,
            status=LOAN_BORROWING,
            requested_at=slip.created_at,
            approved_at=slip.approved_at,
            borrowed_at=slip.borrowed_at,
            due_date=slip.due_date,
            processed_by=admin.id,
        )
        db.session.add(loan)

    # 2. Các lượt mượn ĐÃ QUÁ HẠN (để demo kiểm tra phạt trễ hạn)
    for reader in readers[6:10]:
        book = pool[slip_counter % len(pool)]
        copy = get_available_copy(book)
        if not copy:
            continue
        copy.status = COPY_BORROWED
        book.available_copies = max(0, book.available_copies - 1)
        overdue_d = rnd.randint(3, 10)

        slip = LoanSlip(
            code=make_slip_code(),
            user_id=reader.id,
            slip_type=SLIP_TYPE_DIRECT, # Demo mượn trực tiếp tại quầy
            status=LOAN_BORROWING,
            created_at=now - timedelta(days=14 + overdue_d),
            borrowed_at=now - timedelta(days=14 + overdue_d),
            due_date=today - timedelta(days=overdue_d),
            processed_by=admin.id,
        )
        db.session.add(slip)
        db.session.flush()

        loan = Loan(
            slip_id=slip.id,
            user_id=reader.id,
            book_id=book.id,
            copy_id=copy.id,
            status=LOAN_BORROWING,
            requested_at=slip.created_at,
            borrowed_at=slip.borrowed_at,
            due_date=slip.due_date,
            processed_by=admin.id,
        )
        db.session.add(loan)

    # 3. Các yêu cầu CHỜ LẤY SÁCH TẠI QUẦY (READY_FOR_PICKUP - trong 48h)
    for reader in readers[10:13]:
        book = pool[slip_counter % len(pool)]
        copy = get_available_copy(book)
        if not copy:
            continue
        copy.status = COPY_RESERVED
        book.available_copies = max(0, book.available_copies - 1)

        approved_time = now - timedelta(hours=rnd.randint(4, 20))
        pickup_deadline = approved_time + timedelta(hours=48)

        slip = LoanSlip(
            code=make_slip_code(),
            user_id=reader.id,
            slip_type=SLIP_TYPE_ONLINE,
            status=LOAN_READY,
            created_at=approved_time - timedelta(hours=2),
            approved_at=approved_time,
            pickup_deadline=pickup_deadline,
            processed_by=admin.id,
        )
        db.session.add(slip)
        db.session.flush()

        loan = Loan(
            slip_id=slip.id,
            user_id=reader.id,
            book_id=book.id,
            copy_id=copy.id,
            status=LOAN_READY,
            requested_at=slip.created_at,
            approved_at=slip.approved_at,
            pickup_deadline=slip.pickup_deadline,
            processed_by=admin.id,
        )
        db.session.add(loan)

    # 4. Các yêu cầu CHỜ DUYỆT ONLINE (PENDING)
    for reader in readers[13:16]:
        book = pool[slip_counter % len(pool)]
        slip = LoanSlip(
            code=make_slip_code(),
            user_id=reader.id,
            slip_type=SLIP_TYPE_ONLINE,
            status=LOAN_PENDING,
            created_at=now - timedelta(hours=rnd.randint(1, 12)),
        )
        db.session.add(slip)
        db.session.flush()

        loan = Loan(
            slip_id=slip.id,
            user_id=reader.id,
            book_id=book.id,
            status=LOAN_PENDING,
            requested_at=slip.created_at,
        )
        db.session.add(loan)

    # 5. Các lượt đã trả nhưng CÒN NỢ TIỀN PHẠT TRỄ HẠN (fine_paid=False)
    for reader in readers[1:4]:
        book = pool[slip_counter % len(pool)]
        copy = book.copies[0] if book.copies else None
        fine = rnd.randint(2, 6) * 5000

        slip = LoanSlip(
            code=make_slip_code(),
            user_id=reader.id,
            slip_type=SLIP_TYPE_ONLINE,
            status=LOAN_RETURNED,
            created_at=now - timedelta(days=25),
            borrowed_at=now - timedelta(days=23),
            due_date=today - timedelta(days=9),
            completed_at=now - timedelta(days=2),
            processed_by=admin.id,
        )
        db.session.add(slip)
        db.session.flush()

        loan = Loan(
            slip_id=slip.id,
            user_id=reader.id,
            book_id=book.id,
            copy_id=copy.id if copy else None,
            status=LOAN_RETURNED,
            requested_at=slip.created_at,
            borrowed_at=slip.borrowed_at,
            due_date=slip.due_date,
            returned_at=slip.completed_at,
            fine_overdue=fine,
            fine_amount=fine,
            fine_paid=False,
            processed_by=admin.id,
        )
        db.session.add(loan)

    # 6. Một lượt HƯ HỎNG SÁCH (50% giá sách)
    damaged_reader = readers[4]
    damaged_book = pool[slip_counter % len(pool)]
    damaged_copy = damaged_book.copies[0] if damaged_book.copies else None
    if damaged_copy:
        damaged_copy.status = COPY_DAMAGED
        damaged_copy.condition = "Rách gáy / ướt mép"
        damaged_book.available_copies = max(0, damaged_book.available_copies - 1)

    dmg_fine = int(damaged_book.price * 0.5)
    slip_dmg = LoanSlip(
        code=make_slip_code(),
        user_id=damaged_reader.id,
        slip_type=SLIP_TYPE_DIRECT,
        status=LOAN_RETURNED,
        created_at=now - timedelta(days=10),
        borrowed_at=now - timedelta(days=10),
        due_date=today + timedelta(days=4),
        completed_at=now - timedelta(days=1),
        processed_by=admin.id,
    )
    db.session.add(slip_dmg)
    db.session.flush()

    loan_dmg = Loan(
        slip_id=slip_dmg.id,
        user_id=damaged_reader.id,
        book_id=damaged_book.id,
        copy_id=damaged_copy.id if damaged_copy else None,
        status=LOAN_DAMAGED,
        requested_at=slip_dmg.created_at,
        borrowed_at=slip_dmg.borrowed_at,
        due_date=slip_dmg.due_date,
        returned_at=slip_dmg.completed_at,
        damage_percent=50,
        fine_damage=dmg_fine,
        fine_amount=dmg_fine,
        fine_paid=False,
        note="Độc giả làm rách gáy và ố bìa sách (phạt 50% giá bìa)",
        processed_by=admin.id,
    )
    db.session.add(loan_dmg)

    # 7. Một lượt BÁO MẤT SÁCH (100% giá sách)
    lost_reader = readers[5]
    lost_book = pool[slip_counter % len(pool)]
    lost_copy = lost_book.copies[0] if lost_book.copies else None
    if lost_copy:
        lost_copy.status = COPY_LOST
        lost_book.available_copies = max(0, lost_book.available_copies - 1)

    lost_fine = lost_book.price
    slip_lost = LoanSlip(
        code=make_slip_code(),
        user_id=lost_reader.id,
        slip_type=SLIP_TYPE_DIRECT,
        status=LOAN_RETURNED,
        created_at=now - timedelta(days=20),
        borrowed_at=now - timedelta(days=20),
        due_date=today - timedelta(days=6),
        completed_at=now - timedelta(days=1),
        processed_by=admin.id,
    )
    db.session.add(slip_lost)
    db.session.flush()

    loan_lost = Loan(
        slip_id=slip_lost.id,
        user_id=lost_reader.id,
        book_id=lost_book.id,
        copy_id=lost_copy.id if lost_copy else None,
        status=LOAN_LOST,
        requested_at=slip_lost.created_at,
        borrowed_at=slip_lost.borrowed_at,
        due_date=slip_lost.due_date,
        returned_at=slip_lost.completed_at,
        damage_percent=100,
        fine_overdue=6 * 5000,
        fine_damage=lost_fine,
        fine_amount=lost_fine + 30000,
        fine_paid=False,
        note="Độc giả báo làm mất sách trên xe buýt (bồi thường 100% giá bìa + phạt quá hạn)",
        processed_by=admin.id,
    )
    db.session.add(loan_lost)

    db.session.commit()
    print(f"✓ Tạo các phiếu mượn (LoanSlip) và chi tiết (Loan/LoanItem) mẫu phong phú.")


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

        # 4. Sách & Bản sao BookCopy
        books = _seed_books(cat_cache)

        # 5. Phiếu mượn và Lượt mượn mẫu
        if reset or LoanSlip.query.count() == 0:
            _seed_loans(readers, books if books else Book.query.all(), admin)

        db.session.commit()

        print("\n" + "="*50)
        print("✅ Seed hoàn tất CSDL thành công!")
        print(f"   Admin  : {ADMIN_USER['username']} / {ADMIN_USER['password']}")
        print(f"   Reader : reader01..18 / reader123")
        print("="*50)


if __name__ == "__main__":
    main()
