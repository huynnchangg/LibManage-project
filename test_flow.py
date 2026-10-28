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
    Book, BookCopy, CartItem, Category, Loan, LoanSlip, User,
    LOAN_BORROWING, LOAN_PENDING, LOAN_READY, LOAN_RETURNED,
    COPY_AVAILABLE, COPY_BORROWED, COPY_RESERVED
)

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
    assert db.session.get(Loan, 1).fine_paid is True

print("--- 7. Kiểm tra cho mượn trực tiếp tại quầy (Walk-in Checkout) ---")
ok(cl.post("/admin/loans/checkout", data={"student_query": "11210001", "barcodes": "BC000201", "note": "Mượn trực tiếp tại quầy"}, follow_redirects=True), "lập phiếu mượn")
with app.app_context():
    slip_direct = LoanSlip.query.filter_by(slip_type="direct").first()
    assert slip_direct is not None
    assert slip_direct.status == LOAN_BORROWING
    assert slip_direct.items[0].copy.barcode == "BC000201"

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
