# Câu hỏi phỏng vấn: distributed training và GPU compute

## Data parallel, tensor parallel, pipeline parallel khác nhau thế nào? Bạn chọn theo thứ tự nào?

Data parallel chia dữ liệu, mỗi worker giữ cả model và all-reduce gradient mỗi bước. Tensor parallel chia từng ma trận trong một layer,
giao tiếp activation trong mỗi layer nên cần NVLink và thường chỉ trong một node. Pipeline parallel chia các layer liên tiếp thành stage,
gửi activation giữa stage và chịu bong bóng chờ $$(p-1)/(m+p-1)$$. Thứ tự chọn: model vừa một GPU thì DDP; không vừa thì FSDP/ZeRO (vẫn là
data parallel, chỉ shard trạng thái); chỉ khi FSDP không đủ (layer quá to, hàng trăm GPU, mạng chậm) mới thêm tensor/pipeline parallel, và khi
đó dùng framework làm sẵn.

## DDP đồng bộ gradient thế nào mà không làm chậm backward?

Gradient được gom thành bucket (mặc định khoảng 25 MB) theo thứ tự ngược với forward; bucket nào đủ gradient thì all-reduce bất đồng bộ
ngay trong lúc backward còn tính các layer phía trước, nên giao tiếp chồng lên tính toán. Ring all-reduce gửi khoảng $$2(N-1)/N$$ lần kích
thước gradient mỗi rank, gần như không đổi theo số rank. Lúc bọc model, DDP broadcast tham số từ rank 0 để mọi bản sao bắt đầu giống nhau;
sau đó gradient trung bình giống nhau nên `optimizer.step()` cho cùng tham số trên mọi rank.

## Model 7B chạy inference trên một GPU 80 GB được, sao fine-tune toàn bộ thì không?

Inference chỉ cần tham số bf16: 14 GB. Huấn luyện mixed precision với Adam cần khoảng 16 byte mỗi tham số cho trạng thái model (tham số và
gradient bf16, bản fp32, hai moment Adam): 112 GB, chưa tính activation (hàng chục GB với chuỗi dài). Cách giải: ZeRO/FSDP chia trạng thái
cho N GPU (ZeRO-3 còn 16/N byte mỗi tham số), activation checkpointing, hoặc đổi bài toán (LoRA chỉ huấn luyện vài triệu tham số).

## Giải thích ZeRO-1, 2, 3 và FSDP. Đánh đổi là gì?

ZeRO-1 chia optimizer state, ZeRO-2 thêm gradient, ZeRO-3 thêm tham số; bộ nhớ mỗi GPU lần lượt $$4 + 12/N$$, $$2 + 14/N$$, $$16/N$$ byte mỗi
tham số. ZeRO-1, 2 có giao tiếp như DDP (reduce-scatter thay all-reduce). ZeRO-3 phải all-gather tham số trước forward và trước backward
của mỗi khối, khoảng 1.5 lần giao tiếp của DDP, nhạy với mạng giữa node. FSDP là ZeRO-3 của PyTorch; FSDP2 chia từng tham số thành DTensor.
Đo bộ nhớ thì nhớ `DTensor.numel()` là kích thước toàn cục, phần trên rank là `to_local()`.

## torchrun làm gì? Elastic có nghĩa là gì trong thực tế?

torchrun khởi chạy N tiến trình mỗi node, làm rendezvous (các worker tìm nhau qua TCPStore) và đặt `RANK`, `LOCAL_RANK`, `WORLD_SIZE`,
`MASTER_ADDR`, `MASTER_PORT`. Với rendezvous c10d và `--nnodes=MIN:MAX`, job chấp nhận số node thay đổi; khi một worker hỏng, torchrun dừng
**cả nhóm** và chạy lại script (tối đa `--max-restarts`). Elastic không giữ trạng thái giùm bạn: script phải resume từ checkpoint, không thì
mỗi lần restart là chạy lại từ đầu.

## Sự cố: job 2 tiến trình đứng im không lỗi, CPU 0%, một tiến trình thì chạy bình thường. Bạn điều tra thế nào?

Đứng im với CPU 0% là dấu hiệu chờ trong collective. Xem mỗi rank đứng ở đâu: bước cuối mỗi rank ghi được, `py-spy dump` từng worker,
`TORCH_DISTRIBUTED_DEBUG=DETAIL` để so thứ tự collective. Nghi phổ biến: collective nằm trong nhánh chỉ một rank đi vào (`if rank == 0:` bọc
cả `all_reduce`), dữ liệu chia không đều làm một rank hết batch trước, rendezvous chờ rank không tới. Một tiến trình chạy được vì collective
với world size 1 trả về ngay. Sửa: mọi rank gọi cùng chuỗi collective, `if rank == 0` chỉ bọc tác dụng phụ; ngăn tái diễn bằng CI chạy 2 tiến
trình gloo có timeout và watchdog theo tiến độ thay vì chờ timeout 30 phút của process group.

## Job huấn luyện chạy trên spot. Checkpoint cần những gì để resume ra đúng kết quả?

Tham số, optimizer state (thiếu là Adam bắt đầu lại moment từ 0, kết quả lệch), LR scheduler, bước/epoch, vị trí trong dữ liệu (epoch của
sampler và offset, hoặc thiết kế để thứ tự batch là hàm của số bước), trạng thái RNG, GradScaler. Ghi nguyên tử (tệp tạm, fsync, rename; trên
S3 thì upload xong mới cập nhật con trỏ), một rank ghi với DDP hoặc mỗi rank ghi shard với FSDP (`torch.distributed.checkpoint`). Khởi động
thì tìm bản mới nhất đọc được, bỏ bản hỏng. Chạy lại khi đã xong thì không làm gì (idempotent). Kiểm bằng cách kill thật giữa chừng rồi so
với chạy liền.

## Bao lâu thì nên checkpoint một lần?

Ghi dày tốn thời gian ghi, ghi thưa mất nhiều việc mỗi lần bị thu hồi (trung bình nửa khoảng checkpoint cộng thời gian khởi động lại). Công
thức Young: $$\tau = \sqrt{2\delta M}$$ với $$\delta$$ là thời gian ghi và $$M$$ là thời gian trung bình giữa hai lần hỏng. Ghi 3 phút, hỏng
trung bình 50 giờ một lần: khoảng 2.2 giờ. Với nhiều node, $$M$$ của job nhỏ đi theo số node vì node nào hỏng cũng dừng cả nhóm.

## Thêm GPU có làm job rẻ hơn không? Ước tính chi phí một job thế nào?

Không. Giờ đồng hồ là $$H_1/(N e)$$ nhưng giờ GPU phải trả là $$H_1/e$$; thêm GPU mua thời gian, và khi hiệu suất scale $$e$$ giảm thì còn đắt
hơn. Đòn bẩy giảm tiền là: GPU có giá trên job thấp hơn (nhanh hơn có thể rẻ hơn dù giá giờ cao), spot (cộng phần làm lại kỳ vọng
$$H \lambda (\tau/2 + r)$$), tăng utilization trước khi scale. Ước tính bằng số đo thật trên 1 GPU và hiệu suất đo ở 2, 4, 8 GPU, không bằng
thông số nhà sản xuất.

## GPU utilization chỉ 40%. Bạn làm gì trước khi xin thêm GPU?

Đo thời gian chờ batch tách khỏi thời gian bước (với GPU gọi `torch.cuda.synchronize()` trước khi bấm giờ). Nếu chờ chiếm phần lớn thì là
nghẽn dữ liệu: tăng `num_workers` trong giới hạn core (`num_workers x số rank`), `persistent_workers`, `pin_memory`, gộp tệp nhỏ thành shard,
cache hoặc giải mã trên GPU. Nếu không chờ mà vẫn thấp: batch quá nhỏ, kernel nhỏ, đồng bộ CPU-GPU thừa (`.item()` mỗi bước), giao tiếp không
chồng được. Thêm GPU khi đang nghẽn dữ liệu chỉ nhân chi phí.

## Ray Train và Ray Tune dùng khi nào thay cho torchrun và một vòng lặp tự viết?

Ray Train dựng nhóm worker DDP/FSDP là actor Ray, nên dùng chung cụm với Ray Data (tiền xử lý song song đưa thẳng vào vòng huấn luyện), Tune
và Serve, có chịu lỗi bằng `FailureConfig` cộng checkpoint. Ray Tune chạy nhiều trial song song theo tài nguyên, tách search algorithm (chọn
config) khỏi scheduler (dừng sớm). torchrun đủ khi chỉ cần một job huấn luyện trên Kubernetes/Slurm; Ray đáng giá khi cần nhiều loại workload
trên cùng cụm hoặc tìm siêu tham số quy mô lớn.

## ASHA hoạt động thế nào và có rủi ro gì?

Đặt các mốc tại `grace_period x reduction_factor^k` vòng lặp; trial tới mốc mà không nằm trong top `1/reduction_factor` những trial đã tới
mốc đó thì dừng. Bất đồng bộ: không chờ cả đợt nên tài nguyên không ngồi không, đổi lại trial chạy sớm so với ít đối thủ hơn. Trainable phải
báo metric mỗi vòng, không thì ASHA không làm gì. Rủi ro: dừng nhầm config học chậm lúc đầu nhưng tốt về sau; giảm bằng `grace_period` dài
hơn, metric ít nhiễu, hoặc PBT/BOHB. Chọn trial tốt nhất theo metric cuối (`scope="last"`) để config tái hiện được.

## So sánh PyTorch FSDP, DeepSpeed và Horovod. Bạn chọn gì cho một đội mới?

FSDP2 có sẵn trong PyTorch, không thêm dependency, hệ sinh thái mới (TorchTitan, torchtune) dùng trực tiếp. DeepSpeed có ZeRO 1/2/3 đầy đủ,
offload CPU/NVMe, ZeRO++ cho mạng chậm, pipeline; đổi lại thêm thư viện, config JSON, launcher và định dạng checkpoint riêng. Horovod là ring
all-reduce trên MPI/NCCL độc lập framework, chỉ data parallel, ít được phát triển từ khi có DDP. Đội mới dùng PyTorch: DDP khi vừa, FSDP2 khi
không; DeepSpeed khi cần offload (GPU nhỏ, model lớn) hoặc tính năng FSDP chưa có.

## Bạn được giao 64 GPU spot trong 2 tuần để huấn luyện một model mới. Trình bày kế hoạch.

Bắt đầu nhỏ: 1 GPU đo thông lượng, bộ nhớ, utilization; sửa nghẽn dữ liệu trước. Chọn chiến lược theo bộ nhớ (DDP hay FSDP, hybrid shard nếu
mạng giữa node chậm). Đo hiệu suất scale ở 8, 16, 32, 64 GPU và dừng ở mức hiệu suất còn chấp nhận được. Checkpoint đủ trạng thái, ghi nguyên
tử lên object storage, khoảng checkpoint theo Young với tỉ lệ thu hồi của cả job; kiểm resume bằng kill thật trước khi chạy dài. Ước tính giờ
GPU và tiền cho on-demand và spot, kế hoạch khi không thuê được spot. Vận hành: heartbeat và alert theo tiến độ, timeout cứng, dashboard thông
lượng và chi phí, runbook "kill và resume", tiêu chí rollback về cấu hình nhỏ hơn.
