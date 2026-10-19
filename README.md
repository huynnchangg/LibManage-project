# Hệ thống quản lý mượn trả sách thư viện

Bài tập nhóm – Lập trình Web (Backend: Python/Flask, CSDL: SQLite).

## 1. Phát biểu nhiệm vụ
Số hoá toàn bộ quy trình mượn – trả sách của thư viện trường đại học: độc giả tra cứu và gửi yêu cầu mượn,
thủ thư duyệt – giao – nhận trả, hệ thống tự kiểm soát tồn kho, hạn trả, gia hạn và tiền phạt quá hạn.

## 2. Quy trình xuyên suốt (các chức năng liên kết bằng một thực thể `Loan`)
```
Tra cứu sách → Gửi yêu cầu (pending) → Thủ thư duyệt (borrowing, trừ tồn kho, đặt hạn trả)
            → Gia hạn (tối đa 1 lần) → Trả sách (returned, cộng tồn kho, tính phạt)
            → Thu tiền phạt → Báo cáo thống kê
```
Quy tắc ràng buộc: mỗi độc giả tối đa 5 cuốn đồng thời; không mượn thêm khi còn sách quá hạn hoặc còn nợ phạt;
không mượn trùng sách; hết bản thì không duyệt; phạt 5.000đ/ngày quá hạn. (Chỉnh trong `app/config.py`.)

## 3. Kiến trúc: Monolithic phân lớp (Layered / MVC) + REST API + RBAC
| Lớp | Thư mục | Vai trò |
|---|---|---|
| Presentation (View) | `app/templates`, `app/static` | Giao diện Jinja2 + Bootstrap |
| Controller | `app/blueprints/` (auth, main, admin, api) | Nhận request, kiểm tra quyền, gọi service |
| Service (Business) | `app/services/` | Toàn bộ quy tắc nghiệp vụ, giao dịch |
| Model / Data | `app/models.py` | Thực thể SQLAlchemy ORM |
| Database | SQLite (`instance/library.db`) | Có thể đổi sang MySQL/PostgreSQL qua `DATABASE_URL` |

Bảo mật: băm mật khẩu (werkzeug), RBAC (`admin_required`), CSRF token, ORM chống SQL Injection,
Jinja2 auto-escape chống XSS, security headers, chống open-redirect, cookie HttpOnly/SameSite.

## 4. Mô hình dữ liệu
`User (1)──(n) Loan (n)──(1) Book (n)──(1) Category`  ·  `Loan.processed_by → User (thủ thư)`

## 5. Chức năng
**Độc giả:** đăng ký/đăng nhập, tìm kiếm + lọc sách, xem chi tiết, gửi yêu cầu mượn, huỷ yêu cầu, gia hạn, xem lịch sử và tiền phạt.
**Thủ thư (admin):** dashboard thống kê, CRUD sách & thể loại, khoá/mở khoá độc giả, duyệt/từ chối yêu cầu, nhận trả sách, thu tiền phạt.
**REST API:** `GET /api/v1/books?q=&category=&available=1&page=`, `GET /api/v1/books/<id>`, `GET /api/v1/stats` (admin).

## 6. Chạy dự án
```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed.py      # tạo dữ liệu mẫu
python run.py       # mở http://127.0.0.1:5000
python test_flow.py # kiểm thử luồng nghiệp vụ
```
Tài khoản mẫu: `admin / admin123` · độc giả `sv001, sv002, sv003 / 123456`
(sv002 đang có sách quá hạn và nợ phạt để demo các ràng buộc).

## 7. Phần giao diện (Bạn A phụ trách)
Toàn bộ giao diện nằm trong `app/templates/` và `app/static/` – không dùng Bootstrap, tự xây design system riêng để đồng nhất.

| File | Vai trò |
|---|---|
| `static/css/style.css` | Design system: biến màu, dark mode, button, card, form, bảng, toast, modal… |
| `static/js/app.js` | Hiệu ứng: đếm số, hiện dần khi cuộn, nghiêng 3D, gợi ý tìm kiếm trực tiếp, toast, hộp xác nhận, dark mode |
| `templates/base.html` | Khung chung: navbar, footer, toast, thanh tiến độ cuộn |
| `templates/macros.html` | Component dùng lại: `icon`, `cover`, `meter`, `pager`, `status_badge`, `empty`, `csrf` |
| `templates/index.html`, `book_detail.html` | Tra cứu sách phía độc giả |
| `templates/admin/_layout.html` | Khung sidebar cho mọi trang quản trị |

Quy ước cho cả nhóm: trang mới chỉ cần `{% extends "base.html" %}` (hoặc `admin/_layout.html`) và dùng lại class/macro có sẵn;
nút xoá/thu tiền thêm `data-confirm="..."` vào `<form>` để có hộp xác nhận; tiêu đề/khối cần hiện dần thêm `data-reveal`.
Backend chỉ thay đổi 1 chỗ: `main.index` truyền thêm `stats` (hàm `book_service.public_stats`) cho hero.
