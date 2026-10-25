"""Khởi tạo DB và dữ liệu hệ thống.

Chạy 1 lần khi setup dự án:
    python seed.py

Lần chạy lại sẽ KHÔNG xóa dữ liệu đã có (idempotent).
Dùng --reset để xóa toàn bộ và tạo lại từ đầu (chỉ dùng trên máy cá nhân):
    python seed.py --reset
"""
import sys
from app import create_app
from app.extensions import db
from app.models import User, Category, ROLE_ADMIN, ROLE_READER

app = create_app()

ADMIN = dict(username="admin", email="admin@library.vn",
             full_name="Thủ thư Admin", password="admin123")

DEFAULT_CATEGORIES = [
    "Công nghệ thông tin", "Kinh tế", "Văn học",
    "Khoa học", "Kỹ năng sống", "Lịch sử", "Giáo khoa",
]

with app.app_context():
    reset = "--reset" in sys.argv
    if reset:
        print("⚠️  Reset: xóa toàn bộ DB...")
        db.drop_all()

    db.create_all()

    # --- Admin ---
    if not User.query.filter_by(username=ADMIN["username"]).first():
        admin = User(username=ADMIN["username"], email=ADMIN["email"],
                     full_name=ADMIN["full_name"], role=ROLE_ADMIN)
        admin.set_password(ADMIN["password"])
        db.session.add(admin)
        print(f"✓ Tạo admin: {ADMIN['username']} / {ADMIN['password']}")
    else:
        print(f"– Admin '{ADMIN['username']}' đã tồn tại, bỏ qua.")

    # --- Categories ---
    added_cats = 0
    for name in DEFAULT_CATEGORIES:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
            added_cats += 1
    if added_cats:
        print(f"✓ Thêm {added_cats} thể loại mới.")
    else:
        print("– Thể loại đã đủ, bỏ qua.")

    db.session.commit()
    print("\nHoàn tất. Chạy 'python import_books.py <file.csv>' để nhập sách.")
