"""Validator và index cho collection `reviews` trên MongoDB."""

# TODO: $jsonSchema validator. Bắt buộc ít nhất: _id, order_id, product_id, score, created_at.
#       score là int từ 1 tới 5; created_at là date; answered (nếu có) là bool.
REVIEW_VALIDATOR: dict = {}

# TODO: list index, mỗi index là list (field, 1 | -1), phục vụ:
#   - review mới nhất của một sản phẩm
#   - tra review theo order_id
#   - hàng đợi review điểm thấp chưa trả lời, cũ nhất trước
REVIEW_INDEXES: list[list[tuple[str, int]]] = []
