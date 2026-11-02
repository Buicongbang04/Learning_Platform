# Lời giải: WER và CER cho tiếng Việt

## Cách làm

- `normalize_vi`: `unicodedata.normalize("NFC", text).lower()`, rồi thay mọi ký tự có nhóm category `P`, `S` hoặc `Z`
  bằng dấu cách, cuối cùng `" ".join(...split())`. Thay bằng dấu cách chứ không xoá, để "hiện-tượng" thành hai từ
  "hiện tượng" (đúng như người đọc nghe) và "60.000" thành "60 000".
- `edit_counts`: bảng quy hoạch động, mỗi ô lưu bộ `(tổng, S, D, I)`. Hai token bằng nhau thì kế thừa ô chéo; khác thì
  lấy `min` của ba ứng viên (chéo + S, trên + D, trái + I). So tuple theo tổng trước nên luôn có tổng nhỏ nhất; khi hoà,
  thứ tự tuple chọn một alignment cụ thể, và vì mỗi ứng viên mang theo đúng bộ đếm của đường đi của nó nên
  $$|hyp| = N - D + I$$ luôn đúng.
- `wer`, `cer`: một hàm chung cộng lỗi và cộng $$N$$ trên mọi câu rồi mới chia; `wer` tách bằng `str.split`, `cer`
  dùng `list(chuỗi)` (giữ dấu cách).

Độ phức tạp $$O(nm)$$ mỗi câu, đủ cho câu nói (vài chục từ, vài trăm ký tự). `jiwer` dùng thư viện C (rapidfuzz) cho
cùng phép tính.

## Vì sao các lựa chọn này

- **Mức corpus, không trung bình từng câu.** Câu "xin chào" sai một từ là 50% WER; trung bình theo câu cho câu ngắn
  trọng số bằng câu 30 từ. Mọi benchmark ASR (và `jiwer.wer` với danh sách câu) báo WER mức corpus. Test có một cặp câu
  mà hai cách cho 1/11 và 0.25.
- **Chuẩn hoá cả hai phía, và báo cách chuẩn hoá.** Whisper viết hoa, chấm câu; tham chiếu FLEURS có cột "đã chuẩn hoá"
  riêng. Không chuẩn hoá thì "Việt Nam." so với "việt nam" là hai lỗi. Bài Intermediate 02 đo cùng một bản nhận dạng
  với ba cách chuẩn hoá: chênh lệch đủ lớn để làm hai hệ gần nhau đổi thứ hạng, nên một con số WER không kèm quy tắc chuẩn
  hoá là không so được.
- **CER cho tiếng Việt.** Lỗi hay gặp là sai dấu thanh ("phân" thành "phong", "tân" thành "tăng"): mỗi lỗi như vậy là
  một từ sai trọn vẹn trong WER nhưng chỉ một hai ký tự trong CER. Báo cả hai để biết model "nghe gần đúng" hay "nghe sai hẳn".
- **Không chặn WER ở 1.** Model ảo giác (hallucination) chèn cả câu không có trong audio, một lỗi đặc trưng của Whisper
  khi gặp khoảng lặng; chặn ở 1 giấu mất nó.

## Bẫy thường gặp

- Quên NFC: chuỗi NFD (copy từ macOS, PDF) trông giống hệt nhưng mọi từ có dấu đều thành lỗi.
- Xoá dấu câu thay vì thay bằng dấu cách: "hiện-tượng" thành một từ "hiệntượng".
- Chia cho số từ của câu nhận dạng (hoặc lấy max của hai độ dài): đó không phải WER.
- Giá substitution 2 (bằng deletion + insertion) cho một đại lượng khác (giống khoảng cách của `difflib`), số S bị đẩy
  sang D + I.
