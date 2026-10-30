# Hệ thống quản lý mượn trả sách thư viện

Bài tập nhóm – Lập trình Web (Backend: Python/Flask, CSDL: SQLite).  
Thành viên: **Huyền Trang** (TV1 – UI/Frontend, tester, nghiệp vụ tra cứu sách) · **Khánh Linh** (TV2 – nghiệp vụ mượn/trả) · **Thuận Phạm** (TV3 – auth, CRUD, quản lý độc giả, dashboard, kiến trúc hệ thống)

---

## 1. Phát biểu nhiệm vụ

Số hoá toàn bộ quy trình mượn – trả sách của thư viện trường đại học theo mô hình thực tế: độc giả tra cứu, thêm sách vào giỏ mượn hoặc mượn nhanh 1-click, thủ thư duyệt và giữ sách tại quầy trong 48 giờ, xác nhận giao sách, cho mượn trực tiếp tại quầy bằng mã vạch (Barcode), kiểm tra tình trạng sách khi hoàn trả (hư hỏng 25%–100%, báo mất) và thu tiền phạt minh bạch.

## 2. Quy trình nghiệp vụ chuẩn

```
[ ĐỘC GIẢ ]                                              [ THỦ THƯ TẠI QUẦY ]
                                                            
(MƯỢN ONLINE)                                            (MƯỢN TRỰC TIẾP TẠI QUẦY)
Chọn sách vào Giỏ → Gửi yêu cầu                             Sinh viên mang sách tới quầy
        │                                                           │
        ▼                                                           ▼
Tạo Phiếu mượn (PENDING)                                 Thủ thư nhập Mã SV + Quét Barcode sách
        │                                                           │
        ▼ (Thủ thư gom sách trên kệ)                                ▼
Thủ thư DUYỆT → READY_FOR_PICKUP (Chờ lấy sách)         Tạo phiếu & GIAO SÁCH NGAY
        │ (Giữ chỗ sách trong 48 giờ)                               │
        ▼                                                           │
SV đến quầy đọc Mã phiếu / Mã SV ───────────────────────────────────┤
        │                                                           │
Thủ thư kiểm tra mã vạch & BÀN GIAO SÁCH                            │
        │                                                           │
        ▼                                                           ▼
   BORROWING (Đang mượn — Bắt đầu tính hạn 14 ngày & cho phép gia hạn tối đa 1 lần)
                                │
                                ▼ (SV mang sách tới trả)
                     QUÁ TRÌNH TRẢ & KIỂM TRA SÁCH
                     Thủ thư quét Barcode từng cuốn:
                     ├── 1. Bình thường: Nhập lại kho (Nếu trễ hạn: Phạt 5.000đ/ngày)
                     ├── 2. Bị hỏng (Rách, mất trang): Phạt 25%, 50%, 75% giá bìa
                     └── 3. Báo mất: Đền bù 100% giá sách (+ phạt trễ nếu có)
                                │
                                ▼
                     THANH TOÁN TIỀN PHẠT:
                     ├── Thu tiền mặt/QR ngay lúc trả sách (Đóng phiếu)
                     └── Hoặc Ghi nợ (Tài khoản bị khoá mượn mới cho đến khi trả nợ)
```

Quy tắc ràng buộc (xem `app/config.py`):

| Hằng số | Mặc định | Ý nghĩa |
|---|---|---|
| `LOAN_DAYS` | 14 ngày | Thời hạn mỗi lần mượn sách |
| `PICKUP_HOURS` | 48 giờ | Thời hạn giữ sách tại quầy sau khi thủ thư duyệt online |
| `RENEW_DAYS` | 7 ngày | Số ngày gia hạn thêm mỗi lần |
| `MAX_RENEWALS` | 1 lần | Số lần gia hạn tối đa cho mỗi lượt mượn |
| `MAX_ACTIVE_LOANS` | 5 cuốn | Số sách đang mượn + chờ lấy/duyệt đồng thời |
| `FINE_PER_DAY` | 5.000 đ | Tiền phạt mỗi ngày quá hạn |
| `PER_PAGE` | 12 mục | Số ấn bản hiển thị mỗi trang (tương thích lưới 4-3-2 cột) |

Biểu phí bồi thường hư hại & mất sách:
* **Hư hại nhẹ (25% giá bìa):** Quăn mép, vết bẩn nhỏ, gập trang.
* **Hư hại vừa (50% giá bìa):** Rách bìa ngoài, bong gáy nhẹ, viết vẽ nhiều.
* **Hư hại nặng (75% giá bìa):** Rách mất trang phụ, dính nước/ẩm mốc.
* **Hỏng hoàn toàn / Báo mất (100% giá bìa):** Rách nát không thể phục hồi hoặc làm mất sách.

## 3. Kiến trúc hệ thống: Monolithic phân lớp (MVC) + REST API + RBAC

| Lớp | Thư mục / file | Vai trò |
|---|---|---|
| Presentation | `app/templates/`, `app/static/` | Giao diện Jinja2; Anthropic Paper Design System (Warm Parchment) |
| Controller | `app/blueprints/` (auth, main, admin, api) | Nhận request, kiểm tra quyền, gọi service |
| Service | `app/services/` (book_service, loan_service) | Toàn bộ quy tắc nghiệp vụ, tính toán phạt, giao dịch DB |
| Model | `app/models.py` | Thực thể SQLAlchemy ORM: User, Category, Book, BookCopy, LoanSlip, Loan, CartItem |
| Database | `instance/library.db` (SQLite) | CSDL SQLite nạp sẵn dữ liệu phong phú, đồng bộ cả nhóm qua Git |

Bảo mật: băm mật khẩu (werkzeug), RBAC (`admin_required` decorator), CSRF token (Flask-WTF), ORM chống SQL Injection, Jinja2 auto-escape chống XSS, kích hoạt Foreign Keys SQLite (`PRAGMA foreign_keys=ON`), security headers (`nosniff`, `DENY`), chống open-redirect, cookie `HttpOnly`/`SameSite=Lax`.

## 4. Mô hình dữ liệu mở rộng (ERD)

```
User (1) ── (n) CartItem (n) ── (1) Book
User (1) ── (n) LoanSlip (1) ── (n) Loan (n) ── (1) BookCopy (n) ── (1) Book (n) ── (1) Category
LoanSlip.processed_by → User  (thủ thư duyệt/giao)
```

## 5. Chức năng chính

**Độc giả (Reader):**
* Đăng ký/đăng nhập, đổi mật khẩu.
* Tra cứu, lọc sách theo thể loại, tìm kiếm tức thì.
* **Giỏ mượn sách (Borrow Cart):** Gom nhiều cuốn vào giỏ mượn, gửi phiếu mượn 1 lần.
* **Mượn nhanh 1-click:** Bấm mượn trực tiếp tại trang chi tiết sách.
* **Quản lý mượn trả cá nhân:** Đếm ngược hạn nhận sách 48h, đếm ngược hạn trả 14 ngày, gia hạn trực tuyến (+7 ngày), huỷ yêu cầu khi chưa nhận.
* **In phiếu mượn:** Xem chi tiết phiếu mượn và in ra giấy (CSS Print).

**Thủ thư (Admin):**
* **Dashboard thống kê:** Đồ thị Donut trực quan kho sách, top sách mượn nhiều, độc giả tích cực, cảnh báo nợ phạt.
* **Cho mượn trực tiếp tại quầy:** Nhập mã SV + quét mã vạch (Barcode) xuất sách ngay trong 5 giây.
* **Duyệt mượn trực tuyến:** Gán bản sao vật lý cụ thể, giữ chỗ 48h cho độc giả.
* **Bàn giao sách tại quầy:** Xác nhận độc giả đến nhận sách và bắt đầu tính hạn 14 ngày.
* **Nhận trả sách thông minh:** Tự động tính tiền phạt quá hạn, phạt hư hại 25%–100%, bồi thường mất sách, tùy chọn thu tiền mặt ngay tại quầy.
* **Quản lý sách & Bản sao:** Thêm/sửa sách, đặt giá bìa, quản lý danh sách mã vạch từng cuốn, ẩn/hiện lưu hành.
* **Quản lý thể loại:** Thêm, xóa và **đổi tên thể loại**.
* **Quản lý độc giả:** Phân trang, tìm kiếm, tạo tài khoản độc giả mới, đặt lại mật khẩu (reset password), khóa/mở khóa tài khoản.
* **Quản lý tiền phạt:** Lọc Đã thu / Chưa thu, tìm kiếm, thu tiền phạt.

**REST API JSON (`/api/v1/`):**
* `GET /api/v1/books`: Danh sách sách (hỗ trợ phân trang, tìm kiếm, lọc thể loại).
* `GET /api/v1/books/<id>`: Chi tiết một đầu sách kèm thông tin tồn kho.
* `GET /api/v1/stats`: Thống kê tổng quan hệ thống.

## 6. Cài đặt và chạy

```bash
# 1. Cài đặt thư viện
pip install -r requirements.txt

# 2. Chạy ứng dụng
python run.py       # → http://127.0.0.1:5000

# 3. Chạy kiểm thử tự động toàn diện
python test_flow.py

# 4. Khởi tạo lại CSDL sạch (tuỳ chọn)
python seed.py --reset
```

### Tài khoản mẫu:
* **Admin (Thủ thư):** `admin / admin123`
* **18 Độc giả mẫu:** `reader01` đến `reader18` (mật khẩu chung: `reader123`)
