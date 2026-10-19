"""Tạo dữ liệu mẫu:  python seed.py"""
from datetime import date, datetime, timedelta

from app import create_app
from app.extensions import db
from app.models import Book, Category, Loan, User

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()

    admin = User(username="admin", email="admin@library.vn", full_name="Thủ thư Admin", role="admin")
    admin.set_password("admin123")
    readers = []
    for i, name in enumerate(["Nguyễn Văn An", "Trần Thị Bình", "Lê Minh Cường"], start=1):
        u = User(username=f"sv00{i}", email=f"sv00{i}@neu.edu.vn", full_name=name,
                 student_code=f"11210{i}0", role="reader")
        u.set_password("123456")
        readers.append(u)
    db.session.add_all([admin, *readers])

    cats = {n: Category(name=n) for n in
            ["Công nghệ thông tin", "Kinh tế", "Văn học", "Khoa học", "Kỹ năng sống"]}
    db.session.add_all(cats.values())

    data = [
        ("Clean Code", "Robert C. Martin", "Công nghệ thông tin", 2008, 3),
        ("Designing Data-Intensive Applications", "Martin Kleppmann", "Công nghệ thông tin", 2017, 2),
        ("Fluent Python", "Luciano Ramalho", "Công nghệ thông tin", 2022, 3),
        ("Flask Web Development", "Miguel Grinberg", "Công nghệ thông tin", 2018, 2),
        ("Kinh tế học vi mô", "N. Gregory Mankiw", "Kinh tế", 2020, 4),
        ("Kinh tế học vĩ mô", "N. Gregory Mankiw", "Kinh tế", 2020, 4),
        ("Dế Mèn phiêu lưu ký", "Tô Hoài", "Văn học", 2015, 5),
        ("Số đỏ", "Vũ Trọng Phụng", "Văn học", 2018, 3),
        ("Lược sử thời gian", "Stephen Hawking", "Khoa học", 2016, 2),
        ("Sapiens: Lược sử loài người", "Yuval Noah Harari", "Khoa học", 2019, 3),
        ("Đắc nhân tâm", "Dale Carnegie", "Kỹ năng sống", 2017, 6),
        ("Thinking, Fast and Slow", "Daniel Kahneman", "Kỹ năng sống", 2012, 2),
    ]
    books = []
    for t, a, c, y, n in data:
        books.append(Book(title=t, author=a, category=cats[c], year=y, total_copies=n,
                          available_copies=n, description=f"Sách '{t}' của {a}."))
    db.session.add_all(books)
    db.session.flush()

    def borrow(user, book, days_ago, status="borrowing"):
        start = datetime.now() - timedelta(days=days_ago)
        l = Loan(user_id=user.id, book_id=book.id, status=status, requested_at=start,
                 approved_at=start, due_date=(start + timedelta(days=14)).date(),
                 processed_by=admin.id)
        if status == "returned":
            l.returned_at = start + timedelta(days=10)
        else:
            book.available_copies -= 1
        db.session.add(l)

    borrow(readers[0], books[0], 5)                     # đang mượn, còn hạn
    borrow(readers[1], books[1], 20)                    # quá hạn 6 ngày
    borrow(readers[2], books[2], 30, "returned")        # đã trả đúng hạn
    db.session.add(Loan(user_id=readers[1].id, book_id=books[4].id, status="returned",
                        requested_at=datetime.now() - timedelta(days=40),
                        approved_at=datetime.now() - timedelta(days=40),
                        due_date=date.today() - timedelta(days=26),
                        returned_at=datetime.now() - timedelta(days=21),
                        fine_amount=25000, fine_paid=False, processed_by=admin.id))
    db.session.add(Loan(user_id=readers[0].id, book_id=books[10].id, status="pending"))
    db.session.commit()
    print("Đã tạo dữ liệu mẫu.\n  Admin  : admin / admin123\n  Độc giả: sv001, sv002, sv003 / 123456")
