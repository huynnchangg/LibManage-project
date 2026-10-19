import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-doi-khi-trien-khai")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///library.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Quy tắc nghiệp vụ
    LOAN_DAYS = 14          # số ngày được mượn
    RENEW_DAYS = 7          # mỗi lần gia hạn thêm
    MAX_RENEWALS = 1        # số lần gia hạn tối đa
    MAX_ACTIVE_LOANS = 5    # số sách tối đa (đang mượn + chờ duyệt)
    FINE_PER_DAY = 5000     # VND / ngày quá hạn
    PER_PAGE = 9
