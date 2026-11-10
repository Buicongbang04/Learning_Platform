# Lời giải: Preflight so với REQUIREMENTS.yaml

Lời giải ở `preflight.py` cạnh tệp này. Chạy:

```bash
SOLUTION=1 uv run pytest tracks/fde/modules/01-site-survey/exercises/basic/02-preflight -q
```

## Cách làm

Bốn hàm nhỏ (`check_os`, `check_capacity`, `check_runtime`, `check_access`), mỗi hàm trả danh sách phát hiện, `preflight`
nối lại. Mọi ngưỡng đọc từ `requirements`; hằng số duy nhất là biên 90% cho RAM.

## Vì sao chọn mức như vậy

| Phát hiện | Mức trong lời giải | Lý do |
| --- | --- | --- |
| Đĩa thiếu so với `min_disk_free_gb` | blocker | Image + model + dữ liệu không vừa: cài sẽ dừng giữa chừng. IT phải nới đĩa trước ngày cài, việc này có quy trình riêng (ticket, duyệt) nên phải biết sớm |
| RAM dưới 90% yêu cầu | blocker | LLM và Postgres cùng máy sẽ bị OOM killer chứ không chỉ chậm |
| RAM trong khoảng 90–100% | warning | Máy "4 GB" thật báo `MemTotal` khoảng 3,8 GB; chặn ở đây là chặn nhầm khách đúng cấu hình. Chọn blocker cũng chấp nhận được nếu bạn muốn IT xác nhận bằng văn bản |
| Không sudo + Podman | không báo hoặc warning (lời giải: không báo) | Podman rootless chạy được hoàn toàn ở user thường; đòi sudo là đòi thứ ngân hàng sẽ không cấp |
| Không sudo + Docker | warning (blocker cũng đúng) | User phải thuộc nhóm `docker` (tương đương root, IT ngân hàng thường từ chối) hoặc IT chạy hộ bước cài; có đường đi nhưng phụ thuộc người khác |
| SELinux enforcing | warning | Không phải lý do dừng, nhưng volume cần nhãn `:Z`, và "tắt SELinux cho nhanh" là câu không bao giờ được nói ở ngân hàng |
| `egress` `none`/`proxy` | warning | Sản phẩm vốn giao bằng bundle offline; cảnh báo để nhớ mang đủ và cấu hình proxy + CA (module 02, 03) |
| GPU | không báo | Yêu cầu ghi `optional`: báo "thiếu GPU" là nhiễu |

Ranh giới blocker/warning thực tế: **blocker là thứ phải có người khác làm trước ngày cài**, không phải "thứ nghiêm
trọng". Warning là thứ FDE tự xử lý được trong buổi cài nếu đã chuẩn bị.

## Output trên `hospital` (survey đo thật)

```json
[
  {"check": "mem", "severity": "blocker", "detail": "MemTotal 1971 MB, cần tối thiểu 4096 MB"},
  {"check": "disk", "severity": "blocker", "detail": "Còn trống 6.0 GiB ở /, cần tối thiểu 10 GiB"},
  {"check": "egress", "severity": "warning", "detail": "Ra internet qua proxy http://10.0.2.100:3128: cần cấu hình proxy cho runtime và CA nội bộ"}
]
```

Mã thoát 1. Blocker `mem` có trên mọi VM của lab vì `customer_site()` boot 2048 MB; máy khách thật trong các bài
Advanced có RAM đúng yêu cầu.

## Lỗi hay gặp

- So phiên bản bằng chuỗi hoặc `float("8.10")` (= 8.1, nhỏ hơn 8.9).
- Đặt cứng `10`, `4096`, danh sách OS trong code: yêu cầu đổi theo bản phát hành, test đổi ngưỡng để bắt lỗi này.
- Báo GPU thiếu là blocker; báo `sudo` false là blocker bất kể runtime.
- Trả cả các check "ok" vào danh sách: người đọc phải lọc, và test coi đó là phát hiện thừa.
