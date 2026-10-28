"""CRUD review Olist trên MongoDB. Chạy được với pymongo thật hoặc mongomock."""

from __future__ import annotations

from pymongo import ASCENDING, DESCENDING  # noqa: F401  (dùng cho create_indexes)
from pymongo.database import Database

COLLECTION = "reviews"


def load_reviews(db: Database, reviews: list[dict]) -> int:
    """Ghi review idempotent với _id = review_id. Trả về số document trong collection."""
    # TODO: với mỗi review, tạo doc mới có "_id" = review_id và bỏ khoá "review_id",
    #       rồi replace_one(..., upsert=True). Cuối cùng trả count_documents({}).
    raise NotImplementedError


def low_score_reviews(db: Database, max_score: int = 2) -> list[dict]:
    """Review có score <= max_score, dạng {"review_id", "order_id", "score"}, sort score, review_id."""
    # TODO: find với {"score": {"$lte": max_score}}, projection chỉ lấy order_id và score,
    #       sort theo score rồi _id, đổi _id thành review_id.
    raise NotImplementedError


def reviews_for_product(db: Database, product_id: str, limit: int = 10) -> list[dict]:
    """Review của product_id, created_at giảm dần, tối đa limit."""
    # TODO
    raise NotImplementedError


def answer_review(db: Database, review_id: str, answer: str) -> bool:
    """Đặt answer, answered=True, tăng answer_count. True nếu review tồn tại."""
    # TODO: một lệnh update_one với "$set" và "$inc"
    raise NotImplementedError


def create_indexes(db: Database) -> str:
    """Tạo compound index cho reviews_for_product, trả về tên index."""
    # TODO: Equality (product_id) trước, Sort (created_at giảm dần) sau
    raise NotImplementedError
