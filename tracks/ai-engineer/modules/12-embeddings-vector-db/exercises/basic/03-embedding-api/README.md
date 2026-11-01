---
title: Client embedding kiểu OpenAI - request, base64, chia lô, cache
level: basic
services: []
files:
  - path: starter/embed_client.py
    note: 6 hàm TODO
  - path: tests/test_embed_client.py
    note: Không sửa
  - path: tests/fixtures/
    note: Response thật của Ollama /v1/embeddings
run:
  - uv run pytest tracks/ai-engineer/modules/12-embeddings-vector-db/exercises/basic/03-embedding-api -q
---

## Mục tiêu

Viết phần client mà mọi hệ thống embedding thật cần quanh lời gọi `POST /v1/embeddings`: dựng request đúng chuẩn, đọc
response kể cả dạng base64, chia lô theo giới hạn của server, và cache để không trả tiền (hoặc chờ) embed lại cùng
một văn bản. Làm xong bạn dùng được cùng một client cho OpenAI, Ollama (`/v1/embeddings`), vLLM hay một gateway.

## Đề bài

**Phần cứng:** CPU · ~50 phút

Định dạng request và response ở mục 2 lý thuyết. Trong `starter/embed_client.py`, chỉ dùng thư viện chuẩn và numpy,
không gọi mạng (hàm gửi request được truyền vào dưới tên `embed_fn`):

1. `build_request(texts, model, *, dimensions=None, encoding_format="float") -> dict`: body JSON gồm `model`, `input`
   (list), `encoding_format`; thêm `dimensions` **chỉ khi** được truyền. `ValueError` nếu `texts` rỗng, có văn bản rỗng
   hoặc chỉ gồm khoảng trắng, hoặc `encoding_format` không phải `"float"` / `"base64"`.
2. `parse_response(payload, n_expected=None) -> np.ndarray`: ma trận `float32` theo **thứ tự input**, tức theo trường
   `index` của từng phần tử trong `payload["data"]` (đừng giả định server trả đúng thứ tự). `embedding` là list số hoặc
   chuỗi base64 của các `float32` little-endian. `ValueError` nếu số phần tử khác `n_expected` (khi truyền), các `index`
   không phải đúng `0..n-1`, hoặc các vector khác số chiều.
3. `batched(texts, max_items, max_chars) -> list[list[int]]`: chia chỉ số `0..n-1` thành các lô liên tiếp theo cách tham
   lam: văn bản tiếp theo vào lô hiện tại nếu sau khi thêm, lô có tối đa `max_items` văn bản **và** tổng số ký tự tối đa
   `max_chars`; nếu không thì mở lô mới. Một văn bản dài hơn `max_chars` đứng riêng một lô.
4. `cache_key(model, text) -> str`: sha256 hex của `model` (UTF-8) + một byte `\x00` + `text` (UTF-8).
5. `embed_cached(texts, model, embed_fn, cache, *, max_items=32, max_chars=8000) -> np.ndarray`: trả vector của mọi
   `texts` theo đúng thứ tự (`float32`). Chỉ gửi văn bản chưa có trong `cache` (một `dict` từ `cache_key` tới vector);
   văn bản lặp lại trong cùng lời gọi chỉ gửi **một lần**. Danh sách cần gửi giữ thứ tự xuất hiện đầu tiên, được chia
   bằng `batched`, mỗi lô một lời gọi `embed_fn(list_văn_bản)`. Ghi vector mới vào `cache`.
6. `truncate(vectors, dim) -> np.ndarray`: giữ `dim` chiều đầu rồi chuẩn hoá L2 lại (vector 0 giữ 0), `float32`. Đây là
   cách dùng embedding Matryoshka ở chiều nhỏ hơn (mục 1 lý thuyết).

## Tiêu chí đạt

- Request không có `dimensions` khi không truyền; từ chối input rỗng và encoding lạ.
- `parse_response` sắp theo `index`, giải mã base64 đúng kiểu, bắt response thiếu dòng, trùng `index`, lệch số chiều.
  Hai response thật của Ollama (`tests/fixtures/`, cùng 3 câu, dạng `float` và `base64`) cho cùng ma trận.
- `batched` đúng ở ba bộ giới hạn tính tay và phủ đủ, đúng thứ tự trên 200 văn bản ngẫu nhiên.
- Cache tách theo model; `embed_cached` gửi đúng các lô mong đợi, không gửi lại văn bản đã có, kết quả khớp
  `FakeLLM.embed`.
- `truncate` trả vector đơn vị (hoặc 0).

## Gợi ý

### Gợi ý 1

`np.frombuffer(base64.b64decode(s), dtype=...)`: chọn `dtype` nói rõ cả kích thước (4 byte) lẫn thứ tự byte. Với
`parse_response`, gom vào một `dict` từ `index` tới vector rồi mới kiểm và xếp.

### Gợi ý 2

Trong `embed_cached`, đi một lượt qua `texts` để lập danh sách cần gửi (kiểm cả `cache` lẫn một `set` các khoá đã thêm
trong lượt này), gửi theo lô, ghi vào `cache`, rồi đi lượt thứ hai đọc mọi vector từ `cache` theo thứ tự `texts`.
