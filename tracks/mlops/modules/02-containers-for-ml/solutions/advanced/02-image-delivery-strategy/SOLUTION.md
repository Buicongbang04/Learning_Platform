# Lời giải: chiến lược giao image và model

## Hướng làm

Không có đáp án duy nhất. Bài chấm ở chất lượng đánh đổi và độ cụ thể.

## So sánh ba phương án

| Tiêu chí | Model trong image | Mount từ volume | Tải từ registry model lúc khởi động |
| --- | --- | --- | --- |
| Rollout | Build + đẩy ~500 MB mỗi đêm (layer dependency dùng lại nên thực tế ~30 MB mới) | Chỉ copy file 30 MB, nhưng phải đồng bộ tới 3 máy | Container tự kéo 30 MB |
| Rollback | Chạy lại tag cũ: một thao tác, tái lập tuyệt đối | Phải nhớ file nào ứng với lúc nào | Đổi alias trong registry model |
| Tái lập, kiểm toán | Image digest = model + code, đủ cho "tháng 3 dùng gì" | Cần ghi version ở nơi khác, dễ lệch | Tốt nếu registry giữ lineage (run, commit, data) |
| Điểm hỏng lúc khởi động | Không | Thiếu file, sai quyền | Registry/mạng chết thì replica không lên |
| Registry | 90 đêm x 30 MB model mới = ~2.7 GB (layer dependency chung) | Không đáng kể | Kho model riêng |

Lựa chọn hợp lý: **image gắn model cho production** (rollback và kiểm toán đơn giản, model nhỏ), tách thành hai tầng: image `base` (OS + dependency, đổi hiếm) và image `service` mỗi đêm chỉ thêm code + model (layer mới ~30 MB). Đổi ý khi model lớn tới hàng GB hoặc retrain nhiều lần mỗi giờ: chuyển sang tải từ model registry bằng alias với version ghi trong log.

## Tag

- Immutable: `eta:<git-sha>-m<model-version>`; deploy production luôn tham chiếu **digest** (`@sha256:...`).
- Mutable chỉ để tiện: `staging`, `candidate`; không bao giờ dùng `latest` trong manifest.
- Mối quan hệ ghi trong label OCI (`org.opencontainers.image.revision`, label `model.version`, `data.version`) để từ image truy ngược commit, model và dữ liệu.

## Quét lỗ hổng

Trivy ở ba chỗ: PR (`trivy config` Dockerfile), sau build (quét image, chặn CRITICAL/HIGH có bản vá), định kỳ hằng ngày trên image đang chạy (lỗ hổng mới công bố). Lỗ hổng chưa có bản vá: không chặn nhưng ghi nhận và theo dõi. Ngoại lệ (`.trivyignore` hoặc allowlist) cần người duyệt, lý do và ngày hết hạn.

## Dọn dẹp

Giữ mọi digest đang chạy ở bất kỳ môi trường nào và mọi bản từng lên production trong thời hạn kiểm toán; xoá tag staging cũ hơn 14 ngày, image PR sau khi merge. Không xoá image còn được tham chiếu bởi một bản ghi model đã promote.

## Kế hoạch lỗi

Rollback = đổi digest trong manifest về bản trước đã chạy, rolling update từng replica (vài phút), kèm healthcheck. Điều kiện tiên quyết: giữ digest "last good" trong release record, và test chạy sau rollout (smoke).

## Rubric (tối đa 20 điểm)

| Tiêu chí | Điểm |
| --- | --- |
| So sánh ≥3 phương án theo cùng tiêu chí, có đánh đổi thật | 5 |
| Chọn rõ một phương án và nêu điều kiện đổi ý | 3 |
| Tag: phân biệt mutable/immutable, dùng digest, liên kết commit-model-data | 4 |
| Chính sách trivy cụ thể (chỗ chạy, ngưỡng, unfixed, ngoại lệ hết hạn) | 3 |
| Số liệu ước lượng (dung lượng 90 ngày, thời gian rollout) hợp lý | 3 |
| Kế hoạch rollback có điều kiện tiên quyết | 2 |

Từ 14 điểm trở lên là đạt.
