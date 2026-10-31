# Đặc tả Thiết kế Hệ thống Giao diện (Design System Specification)
> **Thư viện NEU** – Hệ thống quản lý mượn trả sách đại học với phong cách Modern Academic SaaS: giao diện sáng sủa, các góc bo mềm mại, hiệu ứng chuyển màu rực rỡ (Blue & Violet Gradients), hỗ trợ đầy đủ Dark Mode và tương tác mượt mà trên mọi thiết bị.

---

## 1. Triết lý Thiết kế (Design Philosophy)

Giao diện hệ thống Thư viện NEU được xây dựng theo ngôn ngữ **Modern Academic SaaS**, kết hợp giữa tính học thuật trang nhã và trải nghiệm sản phẩm số hiện đại:
- **Tập trung vào nội dung & thị giác:** Tựa sách, bìa sách, trạng thái lưu thông và thời hạn mượn được ưu tiên hiển thị nổi bật với trực quan hóa bằng thanh đo (Meters), nhãn trạng thái (Status Badges) và biểu đồ tròn (Donut Chart).
- **Màu sắc cảm xúc & có chủ đích:** Tông màu xanh hoàng gia (Royal Blue `#2563EB`) kết hợp tím hiện đại (Violet `#7C3AED`) tạo cảm giác chuyên nghiệp, năng động. Các gam màu cảnh báo (Xanh lá, Hổ phách, Đỏ hoa hồng) được sử dụng chính xác theo trạng thái nghiệp vụ.
- **Tương tác có chiều sâu (Depth & Motion):** Kính mờ (Glassmorphism), bóng đổ mềm mang ánh xanh (`rgba(37, 99, 235, 0.25)`), hiệu ứng nghiêng 3D (Tilt) khi rê chuột vào bìa sách, và chuyển cảnh mượt mà với đường cong chuẩn cubic-bezier (`.22, 1, .36, 1`).
- **Hỗ trợ giao diện sáng/tối (Dual Theme):** Tối ưu hóa độ tương phản cho cả chế độ Sáng (Light Mode) và chế độ Ban đêm (Dark Mode), lưu trạng thái qua `localStorage`.

---

## 2. Hệ thống Token Thiết kế (Design Tokens)

### 2.1. Bảng màu (Color Palette)

| Tên Token | Chế độ Sáng (Light) | Chế độ Tối (Dark) | Ý nghĩa & Vai trò sử dụng |
|:---|:---:|:---:|:---|
| `--bg` | `#f4f7fe` | `#0a0f1f` | Nền canvas toàn trang |
| `--surface` | `#ffffff` | `#111933` | Bề mặt Card, Header, Modal, Bảng dữ liệu |
| `--surface-2` | `#f8faff` | `#0e1630` | Bề mặt lớp thứ hai, hover hàng bảng |
| `--text` | `#0f172a` | `#e8edf9` | Màu chữ chính, độ tương phản cao |
| `--muted` | `#64748b` | `#97a3bf` | Màu chữ phụ, mô tả, nhãn phụ, ngày tháng |
| `--line` | `#e3e9f5` | `#222d4d` | Đường viền ngăn cách mảnh (Hairline borders) |
| `--primary` | `#2563eb` | `#4f8bff` | Màu thương hiệu chủ đạo (Royal Blue) |
| `--primary-600` | `#1d4ed8` | `#3b76ee` | Trạng thái hover/active của nút chính |
| `--primary-soft` | `#e8f0ff` | `#16254d` | Nền chip, badge và hover thanh điều hướng |
| `--accent` | `#7c3aed` | `#a78bfa` | Màu tím bổ trợ cho gradient và điểm nhấn |
| `--success` | `#16a34a` | `#34d399` | Sách sẵn sàng, trả thành công, nút hành động an toàn |
| `--success-soft`| `#e7f8ee` | `#0f2a22` | Nền nhãn "Sẵn sàng", "Đã trả", toast thành công |
| `--warn` | `#d97706` | `#fbbf24` | Cảnh báo hạn trả, chờ duyệt, sắp hết sách |
| `--warn-soft` | `#fff4de` | `#2d2410` | Nền nhãn "Chờ duyệt", cảnh báo nợ phạt |
| `--danger` | `#e11d48` | `#fb7185` | Quá hạn, hư hỏng, báo mất, số tiền phạt |
| `--danger-soft` | `#ffe8ed` | `#33141c` | Nền nhãn "Quá hạn", nút xoá, cảnh báo nguy hiểm |

### 2.2. Bảng font chữ & Typography

Hệ thống sử dụng tổ hợp 2 phông chữ tiêu chuẩn quốc tế có hỗ trợ tiếng Việt hoàn hảo:
* **Display Font (Tiêu đề & Thương hiệu):** `'Plus Jakarta Sans', 'Be Vietnam Pro', system-ui, sans-serif`
  - Nét chữ hiện đại, hình học, nét dày `800` mang lại diện mạo dứt khoát và ấn tượng.
* **Body Font (Nội dung văn bản):** `'Be Vietnam Pro', 'Plus Jakarta Sans', system-ui, sans-serif`
  - Tối ưu hóa riêng cho hiển thị dấu tiếng Việt rõ ràng, dễ đọc trong các đoạn văn và bảng biểu.
* **Monospace Font (Mã vạch, Mã phiếu):** `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace`
  - Đảm bảo các ký tự mã vạch (Barcode: `BC...`) và mã phiếu (`PM-...`) hiển thị chuẩn xác, thẳng hàng.

| Cấp bậc | Font | Kích thước | Chiều cao dòng | Độ đậm | Letter Spacing |
|:---|:---|:---:|:---:|:---:|:---:|
| **Hero Display** | Display | 2.2rem – 3.8rem | 1.15 | 800 | -0.03em |
| **Page Title (H1)** | Display | 1.6rem – 2.2rem | 1.20 | 800 | -0.02em |
| **Section Head (H2)** | Display | 1.5rem – 2.1rem | 1.20 | 800 | -0.02em |
| **Card Head (H3)** | Display | 1.05rem – 1.25rem | 1.30 | 700 | -0.01em |
| **Body Base** | Body | 0.94rem – 1.00rem | 1.60 | 400 / 500 | 0 |
| **Body Small / Muted** | Body | 0.85rem – 0.88rem | 1.50 | 400 | 0 |
| **Badge / Caption** | Body | 0.72rem – 0.76rem | 1.20 | 700 | +0.02em |

### 2.3. Bo góc (Border Radius) & Khối hình

* **Pill Shape (`999px`):** Dùng cho Buttons, Badges, Filter Chips, Nav Links, Thanh tìm kiếm nhanh.
* **Card Large (`18px` – `--radius`):** Dùng cho các Card sách, Panel quản trị, Bảng dữ liệu.
* **Container Hero & CTA (`32px`):** Dùng cho khối Hero giới thiệu và Banner kêu gọi hành động.
* **Form Controls (`12px` – `--radius-sm`):** Dùng cho Inputs, Select, Textarea, Phân trang Pager.

### 2.4. Đổ bóng (Elevations & Shadows)

* `--shadow-sm`: `0 1px 2px rgba(15,23,42,.05), 0 2px 8px rgba(15,23,42,.04)` (Thẻ tĩnh, viền nhẹ)
* `--shadow`: `0 10px 30px -10px rgba(37,99,235,.25), 0 4px 12px rgba(15,23,42,.06)` (Thẻ khi hover, nút bấm)
* `--shadow-lg`: `0 30px 60px -20px rgba(37,99,235,.35)` (Hero banner, Modal, Toast notification)

---

## 3. Các Thành phần Giao diện Chuẩn (Components)

### 3.1. Thanh điều hướng đầu trang (Glassmorphic Navbar)
* **Hiệu ứng:** Cố định (`sticky`), nền kính mờ (`backdrop-filter: blur(14px)`), tự động thêm viền mảnh khi cuộn trang.
* **Logo:** Biểu tượng sách nổi bật với góc xoay nhẹ trên nền gradient xanh-tím (`135deg`).
* **Menu điều hướng:** Các pill links bo tròn, nổi bật với màu nền mềm (`--primary-soft`) khi đang ở trang hiện tại.
* **Công cụ:** Nút đổi theme Sáng/Tối (`theme-toggle`), giỏ mượn sách có chấm đỏ hiển thị số lượng (`cart-pill`), avatar người dùng và nút chuyển nhanh vào Quản trị (đối với thủ thư).

### 3.2. Khối Hero & Tra cứu trực tiếp (Live Instant Search)
* **Hiệu ứng thị giác:** Hai khối gradient mềm chuyển động ngẫu nhiên (`.blob.b1`, `.blob.b2`) cùng tiêu đề chữ chuyển màu óng ánh (`.gradient-text`).
* **Thanh tìm kiếm:** Pill search bar lớn với icon kính lúp, tích hợp ô gợi ý kết quả trực tiếp (Live Suggest dropdown) hiển thị ảnh thu nhỏ, tựa sách và tác giả khi gõ phím.
* **Hình ảnh nổi 3D:** 3 bìa sách nghệ thuật đặt chéo góc với chuyển động bập bênh (`animation: bob`) tạo chiều sâu.

### 3.3. Thẻ sách & Bìa sách nghệ thuật (Book Cards & Covers)
* **Bìa sách thật:** Nếu có `cover_url`, hiển thị ảnh chất lượng cao theo tỉ lệ vàng $2:3$, tự động chuyển sang chế độ dự phòng nếu ảnh bị lỗi (`onerror`).
* **Bìa sách đồ họa tự sinh (Fallback CSS Covers):** Nếu sách chưa có ảnh bìa, hệ thống dùng thuật toán gradient theo chuyên mục (`.c0` đến `.c5`) với gáy sách dập bóng nổi và tên sách co dãn tự động theo kích thước vùng chứa (`container-type: inline-size`).
* **Hiệu ứng 3D Tilt:** Khi người dùng rê chuột lên thẻ sách, thẻ sách nghiêng theo góc chuột (`data-tilt="6"`) kèm vệt sáng phản quang.
* **Thanh tồn kho thông minh (`.meter`):** Hiển thị số lượng sách sẵn sàng dưới dạng thanh đo màu:
  - Màu xanh lá: Sách dồi dào ($> 1$ bản).
  - Màu hổ phách nhấp nháy: Sách sắp hết (chỉ còn $1$ bản).
  - Màu đỏ: Hết bản sao vật lý trong kho ($0$ bản).

### 3.4. Hệ thống Quản trị Thư viện (Librarian Admin Portal)
* **Sidebar điều hướng:** Thanh điều hướng cố định bên trái với các mục chức năng có icon SVG chuyên biệt, mục đang chọn được phủ dải màu Gradient rực rỡ và bóng đổ nổi bật.
* **Bảng điều khiển (Dashboard):**
  - Biểu đồ Donut CSS: Thống kê trạng thái kho sách (Hiển thị **99.7% Sẵn sàng** / Đang mượn).
  - Thanh đo Top sách mượn nhiều & Độc giả tích cực: Gradient chuyển sắc tím sang xanh.
* **Quản lý Thể loại:** Tối ưu hóa layout chia 2 cột: Bảng danh sách bên trái (co dãn linh hoạt, chống tràn thanh cuộn ngang `min-width: 0`) và Form tạo thể loại mới cố định bên phải.
* **Quản lý Tiền phạt & Mượn trả:** Bảng dữ liệu có phân trang, nhãn trạng thái trực quan, tích hợp nút xác nhận thu tiền phạt tại quầy kèm lưu vết giao dịch `FinePayment`.

### 3.5. Thông báo Toast & Hộp thoại xác nhận (Toasts & Modals)
* **Toasts:** Xuất hiện ở góc trên bên phải màn hình, có âm hưởng màu theo ngữ cảnh (Thành công, Cảnh báo, Lỗi), đi kèm thanh đếm ngược thời gian hiển thị (`5 giây`).
* **Modals:** Hộp thoại xác nhận trung tâm màn hình với nền làm mờ (`backdrop-filter: blur(4px)`), dùng cho các tác vụ quan trọng như duyệt mượn, từ chối, đặt lại mật khẩu độc giả.

### 3.6. Chế độ In ấn tối ưu (`@media print`)
* Tự động ẩn toàn bộ thanh Navbar, Sidebar, Footer, To-top button và các nút thao tác khi in phiếu mượn (`slip_detail.html`), mang lại bản in phiếu sắc nét, chuẩn trang giấy $A4$/$A5$.

---

## 4. Bố cục & Trải nghiệm Tương thích (Responsive Grid)

| Breakpoint | Mục tiêu thiết bị | Cấu hình bố cục chính |
|:---:|:---|:---|
| **$< 640px$** | Điện thoại di động | Grid sách 1 cột; Navbar chuyển sang menu trượt; Bảng dữ liệu cuộn ngang độc lập |
| **$640px – 900px$** | Máy tính bảng (Tablet) | Grid sách 2 cột; Hero ẩn bìa 3D để tập trung vào tìm kiếm; Sidebar admin chuyển thành thanh cuộn ngang |
| **$900px – 1280px$** | Laptop & Màn hình vừa | Grid sách 3–4 cột; Sidebar admin cố định 240px; Chi tiết sách chia 2 cột (340px / 1fr) |
| **$> 1280px$** | Màn hình lớn (Desktop) | Container tối đa 1180px căn giữa; Thẻ sách dàn 4 cột cân đối; Khoảng đệm thoáng đãng |

---

## 5. Quy chuẩn Viết Code & Mở rộng (Style Guidelines)

1. **Sử dụng CSS Custom Properties:** Mọi thành phần mới phải tái sử dụng các biến trong `:root` (như `var(--primary)`, `var(--radius)`, `var(--shadow)`), không dùng mã màu hard-code.
2. **Không làm vỡ cấu trúc phân tách:** Toàn bộ CSS nằm trong [`frontend/static/css/style.css`](file:///c:/Users/admin/Downloads/library/library/frontend/static/css/style.css), JS tương tác nằm trong [`frontend/static/js/app.js`](file:///c:/Users/admin/Downloads/library/library/frontend/static/js/app.js).
3. **Thân thiện với chuyển động (Reduced Motion):** Luôn tôn trọng tùy chọn của người dùng qua `@media (prefers-reduced-motion: reduce)` để tắt animation nếu người dùng có tiền sử tiền đình.
