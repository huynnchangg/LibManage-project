# Hệ thống quản lý mượn trả sách thư viện

Bài tập nhóm – Lập trình Web (Backend: Python/Flask, CSDL: SQLite).  
Thành viên: **Huyền Trang** (TV1 – UI/Frontend) · **Khánh Linh** (TV2 – nghiệp vụ mượn/trả) · **Thuận Phạm** (TV3 – auth, CRUD, quản lý độc giả, dashboard)

---

## 1. Phát biểu nhiệm vụ

Số hoá toàn bộ quy trình mượn – trả sách của thư viện trường đại học: độc giả tra cứu và gửi yêu cầu mượn, thủ thư duyệt – giao – nhận trả, hệ thống tự kiểm soát tồn kho, hạn trả, gia hạn và tiền phạt quá hạn.

## 2. Quy trình xuyên suốt

```
Tra cứu sách → Gửi yêu cầu (pending) → Thủ thư duyệt (borrowing, trừ tồn kho, đặt hạn trả)
            → Gia hạn (tối đa 1 lần)  → Trả sách (returned, cộng tồn kho, tính phạt)
            → Thu tiền phạt            → Báo cáo thống kê
```

Quy tắc ràng buộc (xem `app/config.py`):

| Hằng số | Mặc định | Ý nghĩa |
|---|---|---|
| `LOAN_DAYS` | 14 ngày | Thời hạn mỗi lần mượn |
| `RENEW_DAYS` | 7 ngày | Số ngày gia hạn thêm |
| `MAX_RENEWALS` | 1 lần | Số lần gia hạn tối đa |
| `MAX_ACTIVE_LOANS` | 5 cuốn | Số sách đang mượn + chờ duyệt đồng thời |
| `FINE_PER_DAY` | 5.000 đ | Phạt mỗi ngày quá hạn |
| `PER_PAGE` | 12 mục | Số sách/bản ghi hiển thị mỗi trang |

Không mượn thêm khi còn sách quá hạn hoặc còn nợ phạt; không mượn trùng sách; hết bản thì không duyệt.

## 3. Kiến trúc: Monolithic phân lớp (MVC) + REST API + RBAC

| Lớp | Thư mục / file | Vai trò |
|---|---|---|
| Presentation | `app/templates/`, `app/static/` | Giao diện Jinja2; design system tự xây (không Bootstrap) |
| Controller | `app/blueprints/` (auth, main, admin, api) | Nhận request, kiểm tra quyền, gọi service |
| Service | `app/services/` | Toàn bộ quy tắc nghiệp vụ, giao dịch DB |
| Model | `app/models.py` | Thực thể SQLAlchemy ORM |
| Database | `instance/library.db` (SQLite) | CSDL SQLite nạp sẵn dữ liệu phong phú, đồng bộ cả nhóm qua Git |

Bảo mật: băm mật khẩu (werkzeug), RBAC (`admin_required` decorator), CSRF token (Flask-WTF), ORM chống SQL Injection, Jinja2 auto-escape chống XSS, kích hoạt Foreign Keys SQLite (`PRAGMA foreign_keys=ON`), security headers, chống open-redirect, cookie `HttpOnly`/`SameSite=Lax`.

## 4. Mô hình dữ liệu

```
User (1)──(n) Loan (n)──(1) Book (n)──(1) Category
Loan.processed_by → User  (thủ thư xử lý)
```

## 5. Chức năng

**Độc giả (Reader):** đăng ký/đăng nhập, đổi mật khẩu, tìm kiếm + lọc sách theo thể loại/tình trạng còn bản, xem chi tiết, gửi/huỷ yêu cầu mượn, gia hạn (có badge đếm số lần và chặn nợ phạt), xem lịch sử và tiền phạt.

**Thủ thư (Admin):** dashboard thống kê, CRUD sách & thể loại, quản lý & khoá/mở khoá độc giả, xem chi tiết từng độc giả kèm lịch sử mượn, duyệt/từ chối yêu cầu, nhận trả sách, thu tiền phạt, đổi mật khẩu, phân trang mượn trả và tối ưu lọc sách quá hạn.

**REST API JSON (`/api/v1/`):**

| Method | Endpoint | Quyền | Mô tả |
|---|---|---|---|
| GET | `/api/v1/books` | Public | Danh sách sách; query: `q`, `category`, `available=1`, `page`, `per_page` |
| GET | `/api/v1/books/<id>` | Public | Chi tiết một cuốn sách |
| GET | `/api/v1/stats` | Admin | Thống kê: `total_titles`, `total_copies`, `readers`, `pending`, `borrowing`, `overdue`, `unpaid` |

## 6. Cài đặt và chạy

File CSDL `instance/library.db` đã được khởi tạo sẵn và commit trực tiếp lên GitHub với dữ liệu mẫu phong phú. Sau khi clone repo, chỉ cần chạy ngay:

```bash
# 1. Cài đúng phiên bản thư viện (đã pin trong requirements.txt)
pip install -r requirements.txt

# 2. Chạy server (đã có sẵn CSDL 800 sách, 18 độc giả, các lượt mượn mẫu)
python run.py       # → http://127.0.0.1:5000

# 3. Kiểm thử luồng nghiệp vụ tự động
python test_flow.py
```

### Tài khoản mẫu có sẵn trong hệ thống:
- **Admin (Thủ thư):** `admin / admin123`
- **18 Độc giả mẫu (Sinh viên NEU):** `reader01` đến `reader18` (mật khẩu chung: `reader123`)

> **Tuỳ chọn:** Dùng lệnh `python seed.py --reset` nếu muốn xóa CSDL và tạo mới lại từ đầu với dữ liệu ngẫu nhiên từ file `books_clean.json` (tổng số bản 1-10 cuốn/đầu sách, phân bổ các trạng thái mượn trả, quá hạn, tiền phạt).

## 7. Dữ liệu sách chuẩn hóa (`books_clean.json`)

Toàn bộ **800 đầu sách** được trích xuất và làm sạch kỹ càng từ nguồn Goodreads, đã loại bỏ mojibake, giải mã thực thể HTML, xử lý trùng lặp mô tả, và xác thực link ảnh bìa thật từ Open Library.

File `books_clean.json` được lưu kèm trong repo để script `seed.py` có thể nạp hoặc khởi tạo lại CSDL bất cứ lúc nào:
- Phân bổ vào **10 thể loại** chuẩn mực (Văn học, CNTT, Kinh tế, Khoa học, Lịch sử...).
- Đầy đủ tiêu đề, tác giả, ISBN, năm xuất bản, nhà xuất bản, mô tả sạch và ảnh bìa.

## 8. Cấu trúc thư mục

```
app/
├── blueprints/
│   ├── auth.py        # TV3 – đăng nhập, đăng ký, đổi mật khẩu, đăng xuất
│   ├── main.py        # TV1+TV2 – trang chủ, chi tiết sách, mượn/huỷ/gia hạn
│   ├── admin.py       # TV3+TV2 – toàn bộ /admin/* (phân trang, tối ưu query quá hạn)
│   └── api.py         # TV3 – REST JSON /api/v1/*
├── services/
│   ├── book_service.py   # TV3 – CRUD sách/thể loại, tìm kiếm, thống kê
│   └── loan_service.py   # TV2 – mượn/trả/gia hạn/phạt/thu tiền
├── templates/
│   ├── admin/
│   │   ├── _layout.html      # sidebar layout chung
│   │   ├── dashboard.html    # thống kê tổng quan
│   │   ├── books.html        # danh sách sách (admin)
│   │   ├── book_form.html    # form thêm/sửa sách
│   │   ├── categories.html   # quản lý thể loại
│   │   ├── users.html        # danh sách độc giả
│   │   ├── user_detail.html  # chi tiết độc giả + lịch sử mượn
│   │   ├── loans.html        # duyệt/từ chối/trả sách + phân trang
│   │   └── fines.html        # thu tiền phạt
│   ├── base.html · macros.html
│   ├── index.html · book_detail.html
│   ├── login.html · register.html · change_password.html · error.html
│   └── my_loans.html
├── static/
│   ├── css/style.css   # design system tự xây + tiện ích layout admin
│   └── js/app.js
├── models.py     # User · Category · Book · Loan + constants
├── config.py     # hằng số nghiệp vụ + cấu hình Flask
└── extensions.py # khởi tạo db, login_manager, csrf
instance/
└── library.db    # CSDL SQLite hoàn chỉnh (800 sách, 18 SV, 42 loans)
books_clean.json  # dữ liệu 800 đầu sách đã làm sạch và chuẩn hóa
seed.py           # script nạp CSDL đầy đủ khi cần reset
run.py            # entry point chạy ứng dụng
test_flow.py      # kiểm thử tích hợp tự động (hỗ trợ console UTF-8)
requirements.txt  # dependencies đã pin version
```

## 9. Giao diện (TV1 — Tái thiết kế theo Anthropic Editorial Design System)

Không dùng framework CSS ngoài, tự xây design system chuẩn mực học thuật lấy cảm hứng từ tài liệu nghiên cứu trên nền giấy da ấm (warm parchment):

| Thành phần | Đặc tả kỹ thuật |
|---|---|
| **Bảng màu tự nhiên** | Nền canvas ngà giấy (`#f0eee6`), bề mặt thẻ ấn phẩm (`#faf9f5`), thẻ tiêu điểm Manilla (`#f5e3c7`), viền hairline mỏng (`#cccbc8`), chân trang đen phiến đá trầm (`#141413`). Điểm nhấn hành động duy nhất dùng tông Đất sét nung Clay (`#d97757`, hover `#c6613f`). Không dùng bóng đổ lòe loẹt hay dải màu tech-blue thông thường. |
| **Typography chuẩn tiếng Việt** | Hệ font kép hỗ trợ Unicode dấu tiếng Việt 100%: **Lora** (Editorial Serif) thể hiện chiều sâu nội dung, tiêu đề tác phẩm và bài viết giới thiệu; **Plus Jakarta Sans** dành riêng cho giao diện điều hướng (UI Chrome, nút bấm, nhãn trạng thái). |
| **Lưới hiển thị & Phân trang** | Cấu hình `PER_PAGE = 12` sách/trang tương thích tối ưu với hệ thống lưới 4 cột (desktop) / 3 cột (tablet) / 2 cột (mobile) đối xứng hoàn hảo, xóa bỏ hoàn toàn hiện tượng lệch hàng hay các ô trống thừa. Chiều cao bìa sách chuẩn tỷ lệ vàng 2:3 với `object-fit: cover`. |
| **Trang chi tiết sách** | Bài viết tóm tắt & giới thiệu tác phẩm định dạng typography báo chí học thuật (`line-height: 1.78`, cỡ chữ 18px, drop-cap chữ cái đầu tao nhã, phân đoạn rành mạch, độ dài dòng chuẩn 72 ký tự). |
| `static/css/style.css` | Hệ thống design tokens, bố cục lưới sách, typography giới thiệu, bảng quản trị, dark mode, modal, toast... |
| `static/js/app.js` | Gợi ý tìm kiếm tức thì, tải gợi ý sách cùng thể loại qua REST API, animation lật thẻ, đếm số động... |

## 10. Kiểm thử

Chạy `python test_flow.py` để test tự động các luồng chính:
- Truy cập trang công khai, API JSON.
- Phân quyền RBAC người dùng thường vs Admin.
- Luồng gửi yêu cầu mượn sách, kiểm tra tồn kho.
- Đổi mật khẩu độc giả và đăng nhập lại bằng mật khẩu mới.
- Admin duyệt yêu cầu mượn, kiểm tra tồn kho giảm.
- Lọc sách quá hạn trực tiếp bằng truy vấn SQL.
- Trả sách quá hạn, tự động tính tiền phạt và ghi nhận thu phạt.
- Khóa / mở khóa tài khoản độc giả.

## 11. Ghi chú Git

File CSDL `instance/library.db` và dữ liệu `books_clean.json` được lưu trữ trực tiếp trong repository để các thành viên trong nhóm và giảng viên khi tải về có thể chạy ngay lập tức. Toàn bộ các file dữ liệu thô cồng kềnh (CSV, ZIP) và script tạm thời đã được dọn dẹp sạch sẽ để repo nhẹ và chuẩn chỉ.
