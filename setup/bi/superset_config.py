"""Cấu hình Superset cho môi trường học local (không dùng cho production)."""
import os

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]
SQLALCHEMY_DATABASE_URI = "sqlite:////app/superset_home/superset.db"
# Cho phép kết nối DB chỉ-đọc về mạng nội bộ Docker (host `postgres`).
PREVENT_UNSAFE_DB_CONNECTIONS = False
# Bài học gọi API bằng requests từ máy host: giữ CSRF bật (clients.py lấy token), tắt giới hạn thời gian CSRF.
WTF_CSRF_TIME_LIMIT = None
