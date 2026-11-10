Viết hàm `slugify(text: str) -> str` trong `slug.py`: bỏ dấu tiếng Việt (kể cả `đ` thành `d`), chữ thường,
mọi chuỗi ký tự không phải chữ hoặc số thành một dấu `-`, không có `-` ở đầu hoặc cuối.
Ví dụ `slugify("Tiếng Việt có dấu!") == "tieng-viet-co-dau"`.
