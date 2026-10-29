import io
import sys
sys.path.insert(0, '.')

# Force stdout/stderr UTF-8 để không bị lỗi ký tự Unicode trên Windows console
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from datetime import date, timedelta
from app import create_app
from app.config import Config
from app.extensions import db
from app.models import (
    Book, BookCopy, CartItem, Category, FinePayment,
    Loan, LoanSlip, User,
    LOAN_BORROWING, LOAN_PENDING, LOAN_READY,
    LOAN_RETURNED, LOAN_CANCELLED,
    COPY_AVAILABLE, COPY_BORROWED, COPY_RESERVED
)
from app.services import loan_service

class T(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False

app = create_app(T)
with app.app_context():
    admin = User(username="admin", email="a@library.vn", full_name="Thủ thư Admin", role="admin")
    admin.set_password("admin123")
    r1 = User(username="r1", email="r1@neu.edu.vn", full_name="Sinh viên R1", student_code="11210001")
    r1.set_password("123456")
    cat = Category(name="CNTT")
    b1 = Book(title="Lập trình Python", author="Tác giả A", category=cat, total_copies=1, available_copies=1, price=100000)
    b2 = Book(title="Cơ sở dữ liệu", author="Tác giả B", category=cat, total_copies=2, available_copies=2, price=120000)
    db.session.add_all([admin, r1, cat, b1, b2])
    db.session.flush()

    # Thêm các BookCopy với mã vạch
    cp1 = BookCopy(book_id=b1.id, barcode="BC000101", status=COPY_AVAILABLE, condition="Tốt")
    cp2_1 = BookCopy(book_id=b2.id, barcode="BC000201", status=COPY_AVAILABLE, condition="Mới")
    cp2_2 = BookCopy(book_id=b2.id, barcode="BC000202", status=COPY_AVAILABLE, condition="Tốt")
    db.session.add_all([cp1, cp2_1, cp2_2])
    db.session.commit()

cl = app.test_client()

def login(u, p):
    return cl.post("/login", data={"username": u, "password": p}, follow_redirects=True)

def ok(resp, txt=None):
    assert resp.status_code == 200, (resp.status_code, resp.data[:300])
    if txt:
        content = resp.get_data(as_text=True)
        assert txt.lower() in content.lower(), f"Expected '{txt}' in response, got snippet: {content[:300]}"
    return resp

print("--- 1. Kiểm tra các trang công khai & API ---")
for url in ["/", "/books/1", "/login", "/register", "/api/v1/books", "/api/v1/books/1"]:
    ok(cl.get(url))

print("--- 2. Kiểm tra RBAC: Reader bị chặn vào /admin/ ---")
assert cl.get("/admin/").status_code == 302
ok(login("r1", "123456"))
assert cl.get("/admin/").status_code == 403

print("--- 3. Kiểm tra Giỏ mượn sách (Borrow Cart) của độc giả ---")
ok(cl.get("/cart"), "giỏ mượn")
ok(cl.post("/cart/add/2", follow_redirects=True), "đã thêm")
ok(cl.get("/cart"), "Cơ sở dữ liệu")
ok(cl.post("/cart/checkout", data={"note": "Lấy vào sáng mai"}, follow_redirects=True), "phiếu mượn")
with app.app_context():
    # Kiểm tra giỏ đã được dọn sạch và tạo phiếu
    assert CartItem.query.filter_by(user_id=2).count() == 0
    slip = LoanSlip.query.filter_by(user_id=2).first()
    assert slip is not None
    assert slip.status == LOAN_PENDING
    assert len(slip.items) == 1

print("--- 4. Mượn nhanh 1-click & kiểm tra chặn mượn trùng ---")
ok(cl.post("/books/1/borrow", follow_redirects=True), "phiếu mượn")
ok(cl.post("/books/1/borrow", follow_redirects=True), "đã mượn hoặc đã gửi")
ok(cl.get("/my/loans"), "chờ duyệt")

print("--- 5. Kiểm tra đổi mật khẩu của độc giả ---")
ok(cl.get("/change-password"), "Đổi mật khẩu")
ok(cl.post("/change-password", data={"old_password": "sai", "new_password": "newpass123", "confirm": "newpass123"}, follow_redirects=True), "không đúng")
ok(cl.post("/change-password", data={"old_password": "123456", "new_password": "newpass123", "confirm": "newpass123"}, follow_redirects=True), "thành công")
cl.post("/logout")
ok(login("r1", "newpass123"))
cl.post("/logout")

print("--- 6. Thủ thư duyệt - giao sách 48h - quá hạn - nhận trả & phạt ---")
ok(login("admin", "admin123"))
for u in ["/admin/", "/admin/loans", "/admin/loans?status=ready", "/admin/loans?status=overdue", "/admin/loans/checkout", "/admin/books", "/admin/categories", "/admin/users", "/admin/fines", "/api/v1/stats"]:
    ok(cl.get(u))

# Duyệt đơn cho mượn cuốn số 2: chuyển sang READY_FOR_PICKUP (chờ lấy 48h)
ok(cl.post("/admin/loans/1/approve", follow_redirects=True), "đã duyệt")
with app.app_context():
    l1 = db.session.get(Loan, 1)
    assert l1.status == LOAN_READY
    assert l1.copy.status == COPY_RESERVED
    assert l1.book.available_copies == 1

# Kiểm tra B02: duyệt lại phiếu đã được duyệt
with app.app_context():
    l1 = db.session.get(Loan, 1)
    stock_before = l1.book.available_copies
    status_before = l1.status
    copy_status_before = l1.copy.status

# Gửi yêu cầu duyệt lần thứ hai
response = cl.post(
    "/admin/loans/1/approve",
    follow_redirects=True
)

# Kiểm tra trạng thái phiếu và tồn kho không thay đổi
with app.app_context():
    l1 = db.session.get(Loan, 1)
    assert l1.status == status_before, "Phiếu đã duyệt bị đổi trạng thái!"
    assert l1.copy.status == copy_status_before, "Trạng thái bản sách bị thay đổi!"
    assert l1.book.available_copies == stock_before, "Tồn kho bị trừ thêm lần nữa!"

print("B02: Đã kiểm tra duyệt lại phiếu, tồn kho không thay đổi.")

# Bàn giao sách tại quầy khi độc giả tới lấy: chuyển sang BORROWING
ok(cl.post("/admin/loans/1/handover", follow_redirects=True), "giao sách")
with app.app_context():
    l1 = db.session.get(Loan, 1)
    assert l1.status == LOAN_BORROWING
    assert l1.copy.status == COPY_BORROWED
    # Giả lập quá hạn 3 ngày
    l1.due_date = date.today() - timedelta(days=3)
    db.session.commit()

# Lọc quá hạn
ok(cl.get("/admin/loans?status=overdue"), "trễ 3 ngày")

# Nhận trả sách: tính phạt 15.000 đ
ok(cl.post("/admin/loans/1/return", data={"condition": "normal", "damage_percent": 0, "pay_now": "0"}, follow_redirects=True), "15.000")
with app.app_context():
    l1 = db.session.get(Loan, 1)
    assert l1.status == LOAN_RETURNED
    assert l1.fine_amount == 15000
    assert l1.fine_paid is False
    assert l1.book.available_copies == 2
    assert l1.copy.status == COPY_AVAILABLE

# Kiểm tra độc giả bị chặn mượn tiếp do nợ phạt
cl.post("/logout")
ok(login("r1", "newpass123"))
ok(cl.post("/books/2/borrow", follow_redirects=True), "tiền phạt chưa thanh toán")


# Thủ thư thu tiền phạt tại quầy
cl.post("/logout")
ok(login("admin", "admin123"))
ok(cl.post("/admin/fines/1/pay", follow_redirects=True), "thu tiền phạt")

with app.app_context():
    l1 = db.session.get(Loan, 1)
    assert l1.fine_paid is True

    # Kiểm tra lịch sử giao dịch thu tiền phạt
    from app.models import FinePayment

    payment = FinePayment.query.filter_by(loan_id=l1.id).first()

    assert payment is not None, "Chưa lưu lịch sử thu tiền phạt!"
    assert payment.amount == l1.fine_amount, "Số tiền thu không chính xác!"
    assert payment.paid_at is not None, "Thiếu thời điểm thu tiền!"
    assert payment.collector_id is not None, "Thiếu thông tin người thu tiền!"

    payment_count_before = FinePayment.query.filter_by(
        loan_id=l1.id
    ).count()

# Thử thu tiền lần thứ hai: không được tạo giao dịch trùng
cl.post("/admin/fines/1/pay", follow_redirects=True)

with app.app_context():
    payment_count_after = FinePayment.query.filter_by(loan_id=1).count()
    assert payment_count_after == payment_count_before, (
        "Lỗi: thu tiền lần hai tạo giao dịch trùng!"
    )

print("B06: Đã kiểm tra thu tiền, lịch sử giao dịch và chống thu trùng.")

print("--- B04: Kiểm tra gia hạn lượt mượn ---")


with app.app_context():
    from app.services.loan_service import LoanError

    # Lấy lại độc giả và sách từ database trong phiên hiện tại
    reader1 = db.session.get(User, 2)
    book2 = db.session.get(Book, 2)

    assert reader1 is not None, "Không tìm thấy độc giả r1"
    assert book2 is not None, "Không tìm thấy sách b2"

    # Tạo độc giả thứ hai để kiểm tra quyền sở hữu
    r2 = User(
        username="r2",
        email="r2@neu.edu.vn",
        full_name="Sinh viên R2",
        student_code="11210002"
    )
    r2.set_password("123456")
    db.session.add(r2)
    db.session.flush()

    # Tạo phiếu mượn
    slip_renew = LoanSlip(
        code="TEST-RENEW-001",
        user_id=reader1.id,
        slip_type="direct",
        status=LOAN_BORROWING,
        due_date=date.today() + timedelta(days=3)
    )
    db.session.add(slip_renew)
    db.session.flush()

    # Tạo lượt mượn
    loan_renew = Loan(
        slip_id=slip_renew.id,
        user_id=reader1.id,
        book_id=book2.id,
        status=LOAN_BORROWING,
        due_date=date.today() + timedelta(days=3),
        renew_count=0,
        fine_amount=0,
        fine_paid=False
    )
    db.session.add(loan_renew)
    db.session.commit()

    # 1. Gia hạn lần đầu phải thành công
    old_due_date = loan_renew.due_date
    loan_service.renew(loan_renew, reader1)

    assert loan_renew.due_date == old_due_date + timedelta(days=7)
    assert loan_renew.renew_count == 1
    assert loan_renew.slip.due_date == loan_renew.due_date

    print("B04.1: Gia hạn lần đầu thành công, hạn trả tăng 7 ngày.")

    # 2. Không cho gia hạn lần thứ hai
    try:
        loan_service.renew(loan_renew, reader1)
        raise AssertionError("Lỗi: hệ thống cho phép gia hạn lần thứ hai!")
    except LoanError:
        pass

    assert loan_renew.renew_count == 1
    print("B04.2: Đã chặn gia hạn vượt quá số lần cho phép.")

    # 3. Không cho gia hạn khi sách đã quá hạn
    loan_renew.renew_count = 0
    loan_renew.due_date = date.today() - timedelta(days=1)
    loan_renew.slip.due_date = loan_renew.due_date
    db.session.commit()

    try:
        loan_service.renew(loan_renew, reader1)
        raise AssertionError("Lỗi: hệ thống cho phép gia hạn sách quá hạn!")
    except LoanError:
        pass

    print("B04.3: Đã chặn gia hạn sách quá hạn.")

    # Đưa hạn trả về tương lai để tiếp tục kiểm tra
    loan_renew.due_date = date.today() + timedelta(days=3)
    loan_renew.slip.due_date = loan_renew.due_date
    loan_renew.renew_count = 0
    loan_renew.fine_amount = 5000
    loan_renew.fine_paid = False
    db.session.commit()

    # 4. Không cho gia hạn khi còn tiền phạt chưa thanh toán
    try:
        loan_service.renew(loan_renew, reader1)
        raise AssertionError("Lỗi: hệ thống cho gia hạn khi còn nợ phạt!")
    except LoanError:
        pass

    print("B04.4: Đã chặn gia hạn khi còn tiền phạt chưa thanh toán.")

    # Xóa khoản phạt để kiểm tra quyền sở hữu
    loan_renew.fine_amount = 0
    loan_renew.fine_paid = False
    db.session.commit()

    # 5. Không cho người khác gia hạn lượt mượn
    other_user = db.session.get(User, r2.id)

    try:
        loan_service.renew(loan_renew, other_user)
        raise AssertionError("Lỗi: hệ thống cho phép người khác gia hạn!")
    except LoanError:
        pass

    print("B04.5: Đã chặn người khác gia hạn lượt mượn.")

print("B04: Hoàn thành 5 trường hợp kiểm thử.")


print("--- 7. Kiểm tra cho mượn trực tiếp tại quầy (Walk-in Checkout) ---")
ok(cl.post(
    "/admin/loans/checkout",
    data={
        "student_query": "11210001",
        "barcodes": "BC000201",
        "note": "Mượn trực tiếp tại quầy"
    },
    follow_redirects=True
), "lập phiếu mượn")

with app.app_context():
    slip_direct = LoanSlip.query.filter_by(
    slip_type="direct"
    ).order_by(LoanSlip.id.desc()).first()

    assert slip_direct is not None, "Không tìm thấy phiếu mượn trực tiếp"
    assert slip_direct.status == LOAN_BORROWING

    assert len(slip_direct.items) > 0, "Phiếu mượn không có lượt mượn"

    direct_loan = slip_direct.items[0]

    assert direct_loan.copy is not None, (
        f"Lượt mượn ID={direct_loan.id} chưa liên kết với bản sách. "
        f"copy_id hiện tại: {direct_loan.copy_id}"
    )

    assert direct_loan.copy.barcode == "BC000201"

    print("Mục 7: Cho mượn trực tiếp tại quầy thành công.")


print("--- 8. Kiểm tra nhận trả sách kèm bồi thường hư hại (50%) ---")
with app.app_context():
    cp_target = BookCopy.query.filter_by(barcode="BC000201").first()
    loan_to_damage = Loan.query.filter_by(copy_id=cp_target.id).order_by(Loan.id.desc()).first()
    loan_dmg_id = loan_to_damage.id

ok(cl.post(f"/admin/loans/{loan_dmg_id}/return", data={"condition": "damaged", "damage_percent": "50", "pay_now": "1", "note": "Rách bìa"}, follow_redirects=True), "60.000")
with app.app_context():
    l_dmg = db.session.get(Loan, loan_dmg_id)
    assert l_dmg.status == "damaged"
    assert l_dmg.damage_percent == 50
    assert l_dmg.fine_damage == 60000
    assert l_dmg.fine_paid is True
    assert l_dmg.copy.status == "damaged"

print("--- 9. Kiểm tra sửa thể loại, thêm sách, đổi mật khẩu độc giả ---")
ok(cl.post("/admin/categories/1/edit", data={"name": "Công nghệ thông tin"}, follow_redirects=True), "cập nhật")
with app.app_context():
    assert db.session.get(Category, 1).name == "Công nghệ thông tin"

ok(cl.post("/admin/books/new", data={"title": "Hệ điều hành", "author": "Tác giả C", "total_copies": "3", "price": "95000", "category_id": "1"}, follow_redirects=True), "đã lưu")
with app.app_context():
    b_new = Book.query.filter_by(title="Hệ điều hành").first()
    assert b_new is not None
    assert len(b_new.copies) == 3
    assert b_new.price == 95000

ok(cl.post("/admin/users/2/reset-password", data={"new_password": "reset123456"}, follow_redirects=True), "đặt lại mật khẩu")
cl.post("/logout")
ok(login("r1", "reset123456"))

print("\n" + "="*50)
print("✅ TẤT CẢ KIỂM THỬ ĐẠT 100%!")
print("="*50)
