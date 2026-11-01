import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Force stdout/stderr UTF-8 để không bị lỗi ký tự Unicode trên Windows console
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from datetime import date, datetime, timedelta
from app import create_app
from app.config import Config
from app.extensions import db
from app.models import (
    Book, BookCopy, CartItem, Category, FinePayment,
    Loan, LoanSlip, User,
    LOAN_BORROWING, LOAN_PENDING, LOAN_READY,
    LOAN_RETURNED, LOAN_CANCELLED,
    COPY_AVAILABLE, COPY_BORROWED, COPY_DAMAGED, COPY_RESERVED
)
from app.services import loan_service
from app.services.loan_service import LoanError

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

# Duyệt đơn cho mượn cuốn số 1: chuyển sang READY_FOR_PICKUP (chờ lấy 48h)
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
response = cl.post("/admin/loans/1/approve", follow_redirects=True)

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

    # Kiểm tra lịch sử giao dịch thu tiền phạt (FinePayment)
    payment = FinePayment.query.filter_by(loan_id=l1.id).first()
    assert payment is not None, "Chưa lưu lịch sử thu tiền phạt!"
    assert payment.amount == l1.fine_amount, "Số tiền thu không chính xác!"
    assert payment.paid_at is not None, "Thiếu thời điểm thu tiền!"
    assert payment.collector_id is not None, "Thiếu thông tin người thu tiền!"

    payment_count_before = FinePayment.query.filter_by(loan_id=l1.id).count()

# Thử thu tiền lần thứ hai: không được tạo giao dịch trùng
cl.post("/admin/fines/1/pay", follow_redirects=True)

with app.app_context():
    payment_count_after = FinePayment.query.filter_by(loan_id=1).count()
    assert payment_count_after == payment_count_before, "Lỗi: thu tiền lần hai tạo giao dịch trùng!"

print("B06: Đã kiểm tra thu tiền, lịch sử giao dịch FinePayment và chống thu trùng.")

print("--- 7. Kiểm tra nghiệp vụ Gia hạn mượn sách (Loan Renewal) ---")
with app.app_context():
    reader1 = db.session.get(User, 2)
    book2 = db.session.get(Book, 2)
    assert reader1 is not None, "Không tìm thấy độc giả r1"
    assert book2 is not None, "Không tìm thấy sách b2"

    # Tạo độc giả thứ hai để kiểm tra quyền sở hữu
    r2 = User(username="r2", email="r2@neu.edu.vn", full_name="Sinh viên R2", student_code="11210002")
    r2.set_password("123456")
    db.session.add(r2)
    db.session.flush()

    # Tạo phiếu mượn và lượt mượn đang trong trạng thái BORROWING
    slip_renew = LoanSlip(
        code="TEST-RENEW-001",
        user_id=reader1.id,
        slip_type="direct",
        status=LOAN_BORROWING,
        due_date=date.today() + timedelta(days=3)
    )
    db.session.add(slip_renew)
    db.session.flush()

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

print("--- 8. Kiểm tra cho mượn trực tiếp tại quầy (Walk-in Checkout) ---")
ok(cl.post(
    "/admin/loans/checkout",
    data={"student_query": "11210001", "barcodes": "BC000201", "note": "Mượn trực tiếp tại quầy"},
    follow_redirects=True
), "lập phiếu mượn")

with app.app_context():
    slip_direct = LoanSlip.query.filter_by(slip_type="direct").order_by(LoanSlip.id.desc()).first()
    assert slip_direct is not None, "Không tìm thấy phiếu mượn trực tiếp"
    assert slip_direct.status == LOAN_BORROWING
    assert len(slip_direct.items) > 0, "Phiếu mượn không có lượt mượn"
    direct_loan = slip_direct.items[0]
    assert direct_loan.copy is not None, f"Lượt mượn ID={direct_loan.id} chưa liên kết với bản sách."
    assert direct_loan.copy.barcode == "BC000201"

print("--- 9. Kiểm tra nhận trả sách kèm bồi thường hư hại (50%) ---")
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

    # Kiểm tra giao dịch FinePayment tự động tạo khi pay_now=True
    dmg_payment = FinePayment.query.filter_by(loan_id=loan_dmg_id).first()
    assert dmg_payment is not None
    assert dmg_payment.amount == 60000

print("--- 10. Kiểm tra sửa thể loại, thêm sách, đổi mật khẩu độc giả an toàn ---")
ok(cl.post("/admin/categories/1/edit", data={"name": "Công nghệ thông tin"}, follow_redirects=True), "cập nhật")
with app.app_context():
    assert db.session.get(Category, 1).name == "Công nghệ thông tin"

ok(cl.post("/admin/books/new", data={"title": "Hệ điều hành", "author": "Tác giả C", "total_copies": "3", "price": "95000", "category_id": "1"}, follow_redirects=True), "đã lưu")
with app.app_context():
    b_new = Book.query.filter_by(title="Hệ điều hành").first()
    assert b_new is not None
    assert len(b_new.copies) == 3
    assert b_new.price == 95000

# Thử đặt mật khẩu ngắn < 6 ký tự -> bị từ chối
ok(cl.post("/admin/users/2/reset-password", data={"new_password": "123"}, follow_redirects=True), "tối thiểu 6 ký tự")

# Đặt mật khẩu hợp lệ >= 6 ký tự -> thành công và không in plain text
res_reset = cl.post("/admin/users/2/reset-password", data={"new_password": "reset123456"}, follow_redirects=True)
ok(res_reset, "thành công")
assert "reset123456" not in res_reset.get_data(as_text=True), "Lỗi bảo mật: in mật khẩu cleartext ra thông báo!"

cl.post("/logout")
ok(login("r1", "reset123456"))
cl.post("/logout")

print("--- 11. Kiểm tra tự động hủy phiếu 'Chờ lấy sách' quá 48h & chặn giao sách ---")
ok(login("admin", "admin123"))
with app.app_context():
    # Giả lập 1 lượt mượn READY_FOR_PICKUP đã quá 48h
    b_test = db.session.get(Book, 1)
    b_test.available_copies = 0
    cp_test = db.session.get(BookCopy, 1)
    cp_test.status = COPY_RESERVED
    db.session.flush()

    slip_exp = LoanSlip(
        code="TEST-EXP-001",
        user_id=2,
        slip_type="online",
        status=LOAN_READY,
        pickup_deadline=datetime.now() - timedelta(hours=5)
    )
    db.session.add(slip_exp)
    db.session.flush()

    loan_exp = Loan(
        slip_id=slip_exp.id,
        user_id=2,
        book_id=b_test.id,
        copy_id=cp_test.id,
        status=LOAN_READY,
        pickup_deadline=datetime.now() - timedelta(hours=5)
    )
    db.session.add(loan_exp)
    db.session.commit()
    loan_exp_id = loan_exp.id

# Thử handover lượt mượn quá hạn -> bị chặn và tự động hủy
res_ho = cl.post(f"/admin/loans/{loan_exp_id}/handover", follow_redirects=True)
with app.app_context():
    l_check = db.session.get(Loan, loan_exp_id)
    assert l_check.status == LOAN_CANCELLED, "Lượt mượn quá hạn 48h chưa được hủy!"
    cp_check = db.session.get(BookCopy, 1)
    assert cp_check.status == COPY_AVAILABLE, "Bản sao chưa được trả về available!"
    b_check = db.session.get(Book, 1)
    assert b_check.available_copies == 1, "Tồn kho sách chưa được hoàn lại!"
    s_check = db.session.get(LoanSlip, l_check.slip_id)
    assert s_check.status == LOAN_CANCELLED, "Trạng thái phiếu mượn chưa được đồng bộ!"
print("Mục 11: Phiếu quá 48h đã tự động hủy, hoàn trả bản sao và cộng lại tồn kho.")

print("--- 12. Kiểm tra phiếu nhiều cuốn không bị đóng nhầm (Slip Status Sync) ---")
with app.app_context():
    slip_multi = LoanSlip(code="TEST-MULTI-001", user_id=2, slip_type="online", status=LOAN_BORROWING)
    db.session.add(slip_multi)
    db.session.flush()

    # Cuốn 1 đang mượn, Cuốn 2 đang chờ duyệt
    item1 = Loan(slip_id=slip_multi.id, user_id=2, book_id=1, status=LOAN_BORROWING, due_date=date.today()+timedelta(days=10))
    item2 = Loan(slip_id=slip_multi.id, user_id=2, book_id=2, status=LOAN_PENDING)
    db.session.add_all([item1, item2])
    db.session.commit()
    item1_id = item1.id
    item2_id = item2.id
    slip_multi_id = slip_multi.id

# Trả cuốn 1
cl.post(f"/admin/loans/{item1_id}/return", data={"condition": "normal", "damage_percent": 0, "pay_now": "0"}, follow_redirects=True)
with app.app_context():
    s_m = db.session.get(LoanSlip, slip_multi_id)
    assert s_m.status == LOAN_PENDING, f"Lỗi đóng nhầm phiếu: cuốn 2 còn pending mà phiếu bị đổi thành {s_m.status}!"
print("Mục 12: Phiếu nhiều cuốn giữ đúng trạng thái khi trả từng phần.")

print("--- 13. Kiểm tra sách ẩn (is_active=False) chặn truy cập và mượn ---")
with app.app_context():
    b_hide = Book.query.filter_by(title="Hệ điều hành").first()
    b_hide.is_active = False
    db.session.commit()
    b_hide_id = b_hide.id

# Truy cập /books/<id> và API /api/v1/books/<id> phải trả về 404
assert cl.get(f"/books/{b_hide_id}").status_code == 404
assert cl.get(f"/api/v1/books/{b_hide_id}").status_code == 404

# Thử mượn 1-click hoặc thêm giỏ phải trả về 404
cl.post("/logout")
ok(login("r1", "reset123456"))
assert cl.post(f"/books/{b_hide_id}/borrow").status_code == 404
assert cl.post(f"/cart/add/{b_hide_id}").status_code == 404
cl.post("/logout")
print("Mục 13: Sách ẩn (is_active=False) đã bị chặn 404 toàn diện.")

print("--- 14. Bắt lỗi nhập % hư hại (chống crash 500) ---")
ok(login("admin", "admin123"))
# Tạo 1 lượt mượn để thử trả sách
with app.app_context():
    slip_ret = LoanSlip(code="TEST-RET-001", user_id=2, slip_type="direct", status=LOAN_BORROWING)
    db.session.add(slip_ret)
    db.session.flush()
    loan_ret = Loan(slip_id=slip_ret.id, user_id=2, book_id=1, status=LOAN_BORROWING, due_date=date.today()+timedelta(days=5))
    db.session.add(loan_ret)
    db.session.commit()
    loan_ret_id = loan_ret.id

# Nhập chữ "abc" vào damage_percent -> không crash 500
resp_err1 = cl.post(f"/admin/loans/{loan_ret_id}/return", data={"condition": "damaged", "damage_percent": "abc"}, follow_redirects=True)
assert resp_err1.status_code == 200
assert "0 đến 100" in resp_err1.get_data(as_text=True)

# Nhập -20 hoặc 150 -> không crash 500, báo lỗi
resp_err2 = cl.post(f"/admin/loans/{loan_ret_id}/return", data={"condition": "damaged", "damage_percent": "150"}, follow_redirects=True)
assert resp_err2.status_code == 200
assert "0% đến 100%" in resp_err2.get_data(as_text=True)
print("Mục 14: Nhập chữ hoặc % hư hại sai quy cách đã được xử lý an toàn.")

print("--- 15. Kiểm tra sửa trạng thái bản sao (BookCopy) & đồng bộ tồn kho ---")
with app.app_context():
    cp_upd = BookCopy.query.filter_by(barcode="BC000101").first()
    b_parent = cp_upd.book
    init_avail = b_parent.available_copies
    cp_upd_id = cp_upd.id
    b_parent_id = b_parent.id

# Đổi bản sao sang "damaged" -> available_copies giảm 1
ok(cl.post(f"/admin/books/{b_parent_id}/copies/{cp_upd_id}/edit", data={"status": "damaged", "condition": "Rách bìa"}, follow_redirects=True), "cập nhật trạng thái")
with app.app_context():
    cp_check = db.session.get(BookCopy, cp_upd_id)
    assert cp_check.status == "damaged"
    b_check = db.session.get(Book, b_parent_id)
    assert b_check.available_copies == init_avail - 1, "Tồn kho không giảm khi bản sao hỏng!"

# Phục hồi bản sao về "available" -> available_copies tăng lại
ok(cl.post(f"/admin/books/{b_parent_id}/copies/{cp_upd_id}/edit", data={"status": "available", "condition": "Đã sửa xong"}, follow_redirects=True), "cập nhật trạng thái")
with app.app_context():
    cp_check = db.session.get(BookCopy, cp_upd_id)
    assert cp_check.status == "available"
    b_check = db.session.get(Book, b_parent_id)
    assert b_check.available_copies == init_avail, "Tồn kho không hồi phục khi bản sao sẵn sàng!"
print("Mục 15: Chức năng sửa trạng thái bản sao hoạt động chuẩn xác và đồng bộ tồn kho.")

print("--- 16. Kiểm tra phân trang và lọc trạng thái độc giả (Users filter & pager) ---")
# Đảm bảo admin đã đăng nhập
cl.post("/logout")
ok(login("admin", "admin123"))

# Kiểm tra trang /admin/users có hiển thị bộ lọc và tab
resp_users = ok(cl.get("/admin/users"))
assert "Đang hoạt động" in resp_users.get_data(as_text=True)
assert "Bị khoá" in resp_users.get_data(as_text=True)

# Khóa độc giả r2
with app.app_context():
    r2_user = User.query.filter_by(username="r2").first()
    r2_id = r2_user.id
ok(cl.post(f"/admin/users/{r2_id}/toggle", follow_redirects=True), "đã khoá")

# Lọc bị khoá -> thấy r2
resp_locked = ok(cl.get("/admin/users?status=locked"))
assert "r2" in resp_locked.get_data(as_text=True)

# Lọc hoạt động -> không thấy r2
resp_active = ok(cl.get("/admin/users?status=active"))
assert "Sinh viên R2" not in resp_active.get_data(as_text=True)

# Mở khoá lại r2
ok(cl.post(f"/admin/users/{r2_id}/toggle", follow_redirects=True), "đã mở khoá")
print("Mục 16: Bộ lọc và phân trang độc giả hoạt động chính xác.")

print("--- 17. Kiểm tra chống mượn trùng sách qua giỏ hàng ---")
# Reader 1 đăng nhập
cl.post("/logout")
ok(login("r1", "reset123456"))

# Thêm sách 1 vào giỏ
with app.app_context():
    # Xoá giỏ cũ nếu có
    CartItem.query.filter_by(user_id=2).delete()
    # Thêm thủ công 1 CartItem cho sách 1 mà reader 1 đang mượn/chờ
    db.session.add(CartItem(user_id=2, book_id=1))
    db.session.commit()

# Checkout giỏ khi sách 1 đang trong lượt mượn -> bị chặn mượn trùng
resp_dup_cart = cl.post("/cart/checkout", data={"note": "Test trùng"}, follow_redirects=True)
assert "đang mượn hoặc đã gửi yêu cầu" in resp_dup_cart.get_data(as_text=True)

# Dọn sạch giỏ
cl.post("/cart/clear", follow_redirects=True)
print("Mục 17: Hệ thống đã chặn mượn trùng thành công ở giỏ hàng.")

print("--- 18. Kiểm tra tìm kiếm lưu thông theo username độc giả ---")
cl.post("/logout")
ok(login("admin", "admin123"))
resp_loan_search = ok(cl.get("/admin/loans?status=all&q=r1"))
assert "r1" in resp_loan_search.get_data(as_text=True)
print("Mục 18: Tìm kiếm lưu thông theo username hoạt động chuẩn xác.")

print("--- 19. Kiểm tra tìm kiếm tiền phạt theo username độc giả ---")
resp_fine_search = ok(cl.get("/admin/fines?q=r1"))
assert "r1" in resp_fine_search.get_data(as_text=True)
print("Mục 19: Tìm kiếm tiền phạt theo username độc giả hoạt động chuẩn xác.")

print("--- 20. Kiểm tra phòng chống XSS (Stored XSS Prevention) ---")
# 1. Đăng ký với tên chứa thẻ HTML độc hại bị chặn
resp_xss_reg = cl.post("/register", data={
    "username": "xss_user",
    "email": "xss@example.com",
    "full_name": "<img src=x onerror=alert(1)>",
    "password": "password123",
    "confirm": "password123"
}, follow_redirects=True)
assert "không được chứa ký tự HTML" in resp_xss_reg.get_data(as_text=True)

# 2. Admin tạo độc giả với tên chứa thẻ HTML độc hại cũng bị chặn
resp_xss_admin = cl.post("/admin/users/new", data={
    "username": "xss_user2",
    "email": "xss2@example.com",
    "full_name": "<script>alert(1)</script>",
    "password": "password123"
}, follow_redirects=True)
assert "không được chứa ký tự HTML" in resp_xss_admin.get_data(as_text=True)
print("Mục 20: Kiểm tra phòng chống Stored XSS hoạt động chuẩn xác.")

print("\n" + "="*50)
print("✅ TẤT CẢ 20 PHÂN HỆ KIỂM THỬ ĐẠT 100%!")
print("="*50)
