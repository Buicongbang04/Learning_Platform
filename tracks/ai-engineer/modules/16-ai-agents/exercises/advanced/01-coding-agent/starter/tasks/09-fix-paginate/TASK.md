`paginate(items, page, size)` trong `pages.py` trả sai trang. Trang đánh số từ 1; trang vượt quá thì trả danh
sách rỗng; `page < 1` hoặc `size < 1` thì ném `ValueError`. Sửa cho đúng.
