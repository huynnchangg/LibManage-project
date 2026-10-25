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

Không mượn thêm khi còn sách quá hạn hoặc còn nợ phạt; không mượn trùng sách; hết bản thì không duyệt.

## 3. Kiến trúc: Monolithic phân lớp (MVC) + REST API + RBAC

| Lớp | Thư mục / file | Vai trò |
|---|---|---|
| Presentation | `app/templates/`, `app/static/` | Giao diện Jinja2; design system tự xây (không Bootstrap) |
| Controller | `app/blueprints/` (auth, main, admin, api) | Nhận request, kiểm tra quyền, gọi service |
| Service | `app/services/` | Toàn bộ quy tắc nghiệp vụ, giao dịch DB |
| Model | `app/models.py` | Thực thể SQLAlchemy ORM |
| Database | `instance/library.db` (SQLite) | Có thể đổi sang MySQL/PostgreSQL qua `DATABASE_URL` |

Bảo mật: băm mật khẩu (werkzeug), RBAC (`admin_required` decorator), CSRF token (Flask-WTF), ORM chống SQL Injection, Jinja2 auto-escape chống XSS, security headers, chống open-redirect, cookie `HttpOnly`/`SameSite=Lax`.

## 4. Mô hình dữ liệu

```
User (1)──(n) Loan (n)──(1) Book (n)──(1) Category
Loan.processed_by → User  (thủ thư xử lý)
```

## 5. Chức năng

**Độc giả (Reader):** đăng ký/đăng nhập, tìm kiếm + lọc sách, xem chi tiết, gửi/huỷ yêu cầu mượn, gia hạn, xem lịch sử và tiền phạt.

**Thủ thư (Admin):** dashboard thống kê, CRUD sách & thể loại, quản lý & khoá/mở khoá độc giả, xem chi tiết từng độc giả kèm lịch sử mượn, duyệt/từ chối yêu cầu, nhận trả sách, thu tiền phạt.

**REST API JSON (`/api/v1/`):**

| Method | Endpoint | Quyền | Mô tả |
|---|---|---|---|
| GET | `/api/v1/books` | Public | Danh sách sách; query: `q`, `category`, `available=1`, `page`, `per_page` |
| GET | `/api/v1/books/<id>` | Public | Chi tiết một cuốn sách |
| GET | `/api/v1/stats` | Admin | Thống kê: `total_titles`, `total_copies`, `readers`, `pending`, `borrowing`, `overdue`, `unpaid` |

## 6. Cài đặt và chạy

```bash
# 1. Cài đúng phiên bản thư viện (đã pin trong requirements.txt)
pip install -r requirements.txt

# 2. Khởi tạo DB + tạo tài khoản admin + thể loại mặc định
python seed.py

# 3. (Tuỳ chọn) Import sách từ file CSV Goodreads
python import_books.py goodreads_books.csv              # toàn bộ
python import_books.py goodreads_books.csv --limit 500  # 500 dòng đầu
python import_books.py goodreads_books.csv --copies 3   # 3 bản/cuốn (mặc định 2)

# 4. Chạy server
python run.py       # → http://127.0.0.1:5000

# 5. (Tuỳ chọn) Kiểm thử luồng nghiệp vụ tự động
python test_flow.py
```

Tài khoản sau khi chạy `seed.py`:
- **Admin:** `admin / admin123`

> Độc giả mẫu (sv001–sv003) đã bị bỏ khỏi `seed.py` để tránh ảnh hưởng DB thật.  
> Dùng `python seed.py --reset` để xoá toàn bộ và tạo lại từ đầu (chỉ dùng trên máy dev).

## 7. Import dữ liệu sách (`import_books.py`)

Đọc CSV định dạng Goodreads, làm sạch dữ liệu và nhập vào DB.

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `<file.csv>` | _(bắt buộc)_ | Đường dẫn tới file CSV |
| `--limit N` | toàn bộ | Chỉ xử lý N dòng đầu |
| `--copies N` | `2` | Số bản mỗi đầu sách |
| `--reset` | tắt | Xoá toàn bộ sách cũ trước khi import |

**Pipeline làm sạch description:**
1. Fix mojibake (UTF-8 bị decode nhầm sang Latin-1)
2. Decode HTML entities (`&amp;`, `&#39;`…)
3. Loại bỏ duplicate (CSV Goodreads nhét preview bị cắt + full text vào cùng 1 field)
4. Cắt đoạn đầu rác (fragment bị cắt giữa câu còn dính sau dedup)
5. Cắt tại ranh giới câu nếu quá `1500` ký tự

**Bộ lọc — bỏ qua sách nếu:**
- Không có title hoặc author
- Description còn dấu hiệu bẩn không sửa được (fragment chữ thường trước chữ hoa, hoặc cụm 3 từ lặp lại 2+ lần trong 400 ký tự đầu)
- Description không phải tiếng Anh (>3% ký tự non-ASCII và <3 stopword tiếng Anh)
- Trùng title + author với sách đã có trong DB

Kết quả thực tế: ~86% sách hợp lệ (428/500 dòng đầu CSV).

## 8. Cấu trúc thư mục

```
app/
├── blueprints/
│   ├── auth.py        # TV3 – đăng nhập, đăng ký, đăng xuất
│   ├── main.py        # TV1+TV2 – trang chủ, chi tiết sách, mượn/huỷ/gia hạn
│   ├── admin.py       # TV3+TV2 – toàn bộ /admin/*
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
│   │   ├── user_detail.html  # chi tiết độc giả + lịch sử mượn  ← TV3
│   │   ├── loans.html        # duyệt/từ chối/trả sách
│   │   └── fines.html        # thu tiền phạt
│   ├── base.html · macros.html
│   ├── index.html · book_detail.html
│   ├── login.html · register.html · error.html
│   └── my_loans.html
├── static/
│   ├── css/style.css   # design system tự xây
│   └── js/app.js
├── models.py     # User · Category · Book · Loan + constants
├── config.py     # hằng số nghiệp vụ + cấu hình Flask
└── extensions.py # khởi tạo db, login_manager, csrf
seed.py           # khởi tạo DB + admin + thể loại
import_books.py   # import sách từ CSV Goodreads
run.py            # entry point
test_flow.py      # kiểm thử tích hợp tự động
requirements.txt  # dependencies đã pin version
```

## 9. Giao diện (TV1)

Không dùng framework CSS ngoài, tự xây design system:

| File | Vai trò |
|---|---|
| `static/css/style.css` | Biến màu, dark mode, button, card, form, bảng, toast, modal, stat cards… |
| `static/js/app.js` | Đếm số động, hiện dần khi cuộn (`data-reveal`), nghiêng 3D card, gợi ý tìm kiếm, toast, hộp xác nhận (`data-confirm`), dark mode |
| `templates/base.html` | Khung chung: navbar, footer, toast, thanh tiến độ cuộn |
| `templates/macros.html` | Reusable components: `icon`, `cover`, `meter`, `pager`, `status_badge`, `empty`, `csrf` |

Quy ước nhóm:
- Trang mới: `{% extends "base.html" %}` hoặc `admin/_layout.html`
- Nút xoá/hành động nguy hiểm: thêm `data-confirm="..."` vào `<form>`
- Khối cần animation: thêm `data-reveal`
- Không thêm CSS inline ngoài trường hợp override biến màu

## 10. Kiểm thử

Chạy `python test_flow.py` để test tự động các luồng chính.  
Checklist kiểm thử tích hợp đầy đủ (TC01–TC20) xem trong file phân công nhóm.

## 11. Ghi chú Git

File `instance/library.db` và `*.csv` đã được thêm vào `.gitignore` — không commit DB hay data file vào repo.  
Mỗi thành viên tự chạy `seed.py` + `import_books.py` trên máy của mình sau khi clone.
