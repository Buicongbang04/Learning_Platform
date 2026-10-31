"""Byte-level BPE tokenizer tự viết, có chuẩn hoá Unicode cho tiếng Việt.

Quy ước (giống GPT-2 / tiktoken):
- Token cơ sở là 256 byte (id 0..255). Merge thứ i tạo token mới id 256 + i.
- Văn bản được chuẩn hoá NFC, rồi tách thành "pretoken" bằng PRETOKEN_RE; merge không bao giờ
  vượt qua ranh giới pretoken (một token không chứa nửa từ này nửa từ kia).
"""

import re
import unicodedata
from collections import Counter

# Từ (chữ cái/số, kể cả chữ có dấu tiếng Việt) kèm tối đa một dấu cách đứng trước; cụm dấu câu kèm
# dấu cách đứng trước; cụm khoảng trắng. Ghép các pretoken lại đúng bằng văn bản gốc.
PRETOKEN_RE = re.compile(r" ?[^\W_]+| ?[^\s\w]+| ?_+|\s+(?!\S)|\s+")


def normalize(text: str) -> str:
    """Chuẩn hoá Unicode về dạng NFC (dấu tổ hợp gộp vào chữ cái)."""
    # TODO
    raise NotImplementedError


def pretokenize(text: str) -> list[str]:
    """Chuẩn hoá NFC rồi tách thành pretoken theo PRETOKEN_RE. "".join(kết quả) == normalize(text)."""
    # TODO
    raise NotImplementedError


def train_bpe(texts: list[str], vocab_size: int) -> list[tuple[int, int]]:
    """Học danh sách merge (theo thứ tự) để từ điển có tối đa `vocab_size` token (kể cả 256 byte).

    Mỗi vòng: đếm mọi cặp token liền nhau trong từng pretoken (nhân với tần suất pretoken), chọn cặp
    nhiều nhất; hoà thì chọn cặp có (id trái, id phải) nhỏ nhất. Dừng sớm khi cặp tốt nhất xuất hiện < 2 lần.
    """
    # TODO: đếm tần suất từng pretoken một lần (Counter), biểu diễn mỗi pretoken là list id byte,
    # rồi lặp: đếm cặp, chọn cặp tốt nhất, thay cặp đó bằng id mới trong mọi pretoken.
    raise NotImplementedError


def encode(text: str, merges: list[tuple[int, int]]) -> list[int]:
    """Văn bản → danh sách id. Trong mỗi pretoken, lặp lại: ghép cặp có thứ hạng merge thấp nhất."""
    # TODO
    raise NotImplementedError


def decode(ids: list[int], merges: list[tuple[int, int]]) -> str:
    """Danh sách id → văn bản. Byte UTF-8 không hợp lệ thay bằng U+FFFD."""
    # TODO: dựng bảng id → bytes từ 256 byte cơ sở và các merge, nối bytes rồi giải mã MỘT lần
    raise NotImplementedError
