# Lời giải: tìm commit làm mất miễn phí ship bằng git bisect run

Hai script đầy đủ ở `check_free_shipping.sh` và `find_first_bad.sh` cạnh tệp này.

## Cách làm

1. **Script kiểm tự chọn exit code.** Toàn bộ phần gọi hàm nằm trong `try/except Exception` của Python. Gặp lỗi thì
   `sys.exit(125)`, nghĩa là "commit này không kiểm được", bisect bỏ qua và thử commit lân cận. Chỉ khi gọi được hàm
   mới so kết quả: `0` là good, `1` là bad.
2. **`python3 -B`.** Không ghi `__pycache__`. Bisect checkout hàng chục commit trong vài giây; Python kiểm `.pyc` theo
   mtime (giây) và kích thước nguồn, nên hai phiên bản cùng kích thước sửa trong cùng giây có thể dùng nhầm bytecode cũ.
   Tệp rác trong working tree còn có thể làm `git checkout` từ chối khi một commit sau thêm đúng tệp đó vào Git.
3. **`trap cleanup EXIT` trước `git bisect start`.** Mọi đường thoát, kể cả `set -e` dừng giữa chừng, đều chạy
   `git bisect reset`. Người dùng script sẽ không bao giờ thấy repo kẹt ở "You are currently bisecting".
4. **Đọc `refs/bisect/bad` thay vì parse output.** Output của `git bisect run` là văn bản cho người đọc, đổi theo phiên
   bản Git. Khi bisect kết thúc, `refs/bisect/bad` trỏ đúng vào commit lỗi đầu tiên.
5. **stdout chỉ có kết quả.** Output của git đi sang stderr, stdout là `first-bad <sha>`, để script khác (bot comment
   lên issue, job CI) dùng được.

## Vì sao exit `125` quan trọng

Với bố cục A, commit 24–25 có `shipping.py` lỗi cú pháp và commit 28–29 thiếu `rates.json`. Script ngây thơ
(`tests/fixtures/naive_check.sh`, chỉ `python3 -c 'assert ...'`) trả `1` cho các commit đó. Bisect tin rằng lỗi đã có
từ commit 28 và báo sai thủ phạm: test `test_naive_check_is_caught` chạy đúng tình huống này. Trong đời thật, kết quả
sai đó dẫn tới revert nhầm commit, còn bug thật vẫn ở lại.

Phân loại đúng cần chuẩn:

| Kết quả | Exit | Ví dụ |
| --- | --- | --- |
| Hành vi đúng | `0` | Phí `0` cho đơn 200 BRL |
| Hành vi sai **đúng loại bug đang tìm** | `1` | Phí `21` |
| Không build, không import, lỗi môi trường, bug **khác** | `125` | `SyntaxError`, thiếu tệp, test khác hỏng |
| Bản thân script hỏng, cần dừng hẳn | `>= 128` | Không tìm thấy `python3` (script nên tự kiểm và exit `255`) |

## Số bước

Bisect là tìm kiếm nhị phân: 48 commit cần khoảng log2(48), tức 6 lần kiểm, cộng vài lần cho commit bị skip. Kiểm
thủ công 6 lần đã đỡ, nhưng giá trị thật của `bisect run` là chạy không người trông: một test tích hợp 5 phút trên 500
commit xong trong chưa tới một giờ.

## Bisect trong thực tế

- **Lịch sử nhiều commit không build được** (commit "wip", squash kém) làm bisect phải skip nhiều, có khi kết thúc bằng
  "only skipped commits left" và một danh sách nghi phạm. Đây là một lý do để mỗi commit trên `main` đều qua CI.
- **Merge commit**: bisect đi vào cả nhánh được merge. `git bisect start --first-parent` (Git 2.29+) chỉ đi theo
  first-parent của `main`, hợp khi mỗi PR là một merge commit và bạn chỉ muốn biết PR nào gây lỗi.
- **Lỗi không tất định** (flaky): chạy test vài lần trong script, chỉ trả `1` khi lỗi lặp lại, nếu không thì trả `125`.
- **Đặt tên lại good/bad** cho việc không phải bug: `git bisect start --term-old=slow --term-new=fast` để tìm commit làm
  một truy vấn nhanh lên.
