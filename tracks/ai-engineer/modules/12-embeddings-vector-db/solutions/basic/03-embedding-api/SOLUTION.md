# Lời giải: client embedding kiểu OpenAI

## Cách làm

**`build_request`.** Ép `texts` thành `list` (JSON không có tuple), kiểm ba điều kiện rồi dựng `dict`; `dimensions` chỉ
thêm khi khác `None`. API của OpenAI từ chối cả request nếu một phần tử `input` rỗng, và một số server (vLLM, Ollama với
model không hỗ trợ) báo lỗi với khoá lạ, nên đừng gửi `dimensions: null`.

**`parse_response`.** Gom `index -> vector` vào `dict`: chuỗi thì `np.frombuffer(base64.b64decode(s), dtype="<f4")`, list
thì `np.asarray(..., dtype=np.float32)`. Kiểm khoá đúng là `0..n-1`, số dòng khớp `n_expected`, các vector cùng shape, rồi
xếp theo `index`. `"<f4"` nói rõ 4 byte little-endian; `np.float64` đọc sai độ dài (nửa số phần tử, giá trị rác), `">f4"`
đọc sai thứ tự byte.

**`batched`.** Một vòng tham lam: trước khi thêm văn bản `i`, nếu lô hiện tại **khác rỗng** và việc thêm làm vượt
`max_items` hoặc `max_chars` thì đóng lô. Điều kiện "khác rỗng" làm văn bản quá dài tự đứng một mình thay vì tạo lô rỗng.

**`cache_key`.** `hashlib.sha256(model_bytes + b"\x00" + text_bytes).hexdigest()`. Byte phân cách để `("ab", "c")` và
`("a", "bc")` khác khoá.

**`embed_cached`.** Lượt một: lập danh sách cần gửi, bỏ văn bản đã có trong `cache` hoặc đã thêm trong lượt này (một `set`
khoá). Gửi theo `batched`, ghi vào `cache`. Lượt hai: đọc mọi vector từ `cache` theo thứ tự `texts`.

**`truncate`.** Cắt `[..., :dim]` rồi chuẩn hoá lại như `l2_normalize` của Basic 01.

## Số đo liên quan

- Fixture là response thật của Ollama `/v1/embeddings` (`nomic-embed-text`, `dimensions=8`, ba câu, chụp ngày 2026-11-01):
  dạng `float` và `base64` cho cùng ma trận, `usage.prompt_tokens` là 20 cho ba câu.
- Base64 của `float32` dài khoảng $$4 \cdot 4/3$$ byte mỗi số, so với 10 tới 12 ký tự mỗi số khi in thập phân trong JSON:
  response nhỏ hơn khoảng 2 tới 3 lần và không mất chính xác khi parse.
- Cache có lợi thật: bài Intermediate 01 embed 61 425 điều Zalo Legal mất khoảng 45 phút trên laptop GPU 4GB theo số đo của module 13 (2 790 giây, tức 47 phút trên PC của
  track khi GPU dùng chung); embed lại cùng corpus mỗi lần chạy notebook là lãng phí lớn nhất của một
  pipeline RAG mới viết.

## Vì sao khoá cache phải có model

Vector của hai model khác nhau sống trong hai không gian khác nhau (khác cả số chiều: `bge-m3` 1 024, `nomic-embed-text`
768), và kể cả cùng số chiều thì cosine giữa chúng vô nghĩa. Đổi model mà dùng lại cache theo khoá chỉ có text thì index
trộn hai không gian, search sai im lặng. Hệ thống thật thêm cả phiên bản tiền xử lý (chuẩn hoá NFC, tiền tố
`search_document:`, cắt độ dài) vào khoá vì chúng cũng đổi vector.

## Bẫy thường gặp

- Tin rằng `data` luôn theo thứ tự `input`: đặc tả có trường `index` vì không phải server nào cũng đảm bảo điều đó.
- Không kiểm số dòng: server trả thiếu một vector (lỗi một phần) làm mọi vector sau lệch một dòng.
- Gửi trùng: corpus thật có nhiều đoạn lặp (tiêu đề, điều khoản chuẩn), dedup trong lô tiết kiệm trực tiếp tiền và thời gian.
- Cắt chiều mà không chuẩn hoá lại: tích vô hướng không còn là cosine.
