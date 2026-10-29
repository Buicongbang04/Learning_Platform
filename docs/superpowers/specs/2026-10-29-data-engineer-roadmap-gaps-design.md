# Thiết kế: lấp chỗ thiếu của track Data Engineer theo roadmap PDF

Ngày: 2026-10-29. Nguồn đối chiếu: `roadmap/data-engineer.pdf` (bản PDF của roadmap.sh/data-engineer).

## 1. Mục đích và lý do

Track `data-engineer` đã có 11 module, 89 bài tập, capstone Olist. Đối chiếu từng node của roadmap
PDF với nội dung cho thấy hai lỗ hổng lớn (phần mở đầu Introduction / Data Engineering Lifecycle /
Data Generation không có; hybrid ingestion gần như không có) và một loạt mục còn mỏng. Cùng lúc,
người học muốn **luyện trên dữ liệu thật** thay cho dữ liệu tự sinh: mỗi bộ dữ liệu thật có insight
và độ bẩn riêng, đó mới là thứ cần học.

Người học: nền DA/DS (Python, pandas, SQL khá), đang học DE để đi làm. Đọc tiếng Việt, giữ thuật ngữ
tiếng Anh. Làm bài trong VS Code, app học tập chạy local (`app/`).

## 2. Mục tiêu, ngoài phạm vi, điều cấm

**Mục tiêu**
- Phủ đủ mọi node của roadmap PDF, mỗi node có nội dung đủ sâu (không chỉ một câu nhắc tên).
- Bài thực hành mới dùng **dữ liệu thật**, có sẵn cách tải; mở notebook là chạy được ngay.
- **Mỗi bài thực hành với dữ liệu thật phải ra 4 sản phẩm** (người học chốt):
  1. dữ liệu sạch thật (lưu ra tệp, vd. Parquet),
  2. insight có số liệu cụ thể từ chính bộ dữ liệu,
  3. biểu đồ minh hoạ, vẽ bằng code ngay trong notebook,
  4. ~~báo cáo ngắn về bộ dữ liệu~~ (đã thay bằng trắc nghiệm trong app, xem spec `2026-10-29-notebook-panel-quiz-design.md`;
     không còn `report.md` với các heading Bộ dữ liệu / Làm sạch / Insight / Giới hạn).
- Capstone cuối track là **dự án hoàn chỉnh trên dữ liệu thật, có dashboard xem trên trình duyệt**.

**Ngoài phạm vi**
- Chuyển các bài tập cũ (dạng `.py`/`.sql`) sang notebook. Bài cũ giữ dạng script (người học chốt).
- Render hay chạy notebook bên trong web app. App chỉ cần nút mở notebook trong VS Code.
- Dashboard trên trình duyệt cho bài thường (chỉ capstone cuối mới cần).
- Bộ dữ liệu hàng chục GB: Spark chỉ cần 1–3 GB, đủ thấy khác biệt khi tối ưu (người học chốt).
- MLOps sâu: để cho track `mlops`. Ở đây chỉ một phần "Data cho ML".

**Điều cấm (làm vậy là hỏng dù chạy được)**
- Bài dữ liệu thật mà làm xong không có dữ liệu sạch, insight, biểu đồ, trắc nghiệm bài học (trước đây là báo cáo).
- Bài "dữ liệu thật" nhưng nhạt: không cho thấy điều gì thú vị về bộ dữ liệu.
- Module 00 chỉ toàn lý thuyết chung chung, không có thực hành thu thập dữ liệu thật.
- Test cần mạng hay cần bộ dữ liệu đầy đủ mới chạy: phần dùng dữ liệu thật phải tự skip khi chưa tải.
- Làm mất tiến độ đã lưu của người học (xem ràng buộc về heading ở mục 3).
- Phá vỡ track DE, track AI & Data Scientist đang làm song song, hay app.

## 3. Ràng buộc

- Theo đúng `CONTENT_SPEC.md` (cấu trúc thư mục, frontmatter, interview, milestone).
- **Không đổi tên, không xoá, không đánh số lại heading `## ` đã có** trong README module: slug của
  heading là khoá tiến độ "đã đọc" trong `progress.json`. Thêm nội dung vào module cũ bằng `###` bên
  trong phần sẵn có. Module mới thì tự do.
- Không sửa `data/generate_olist.py` (track DE còn dùng cho test và làm phương án dự phòng).
- **Dùng chung hạ tầng track AI & Data Scientist đã chốt** (xem
  `docs/superpowers/specs/2026-10-29-ai-data-scientist-track-design.md` mục 5):
  - notebook chấm bằng pytest qua `testkit.Exercise.notebook(...)`, cùng cơ chế `SOLUTION=1`;
  - bộ dữ liệu khai báo trong danh mục `data/download_dataset.py`, tải vào `data/raw/<bộ>/`
    (không commit), có nguồn và giấy phép; Kaggle dùng `KAGGLE_API_TOKEN` trong `setup/.env`
    (đã có, đã kiểm chứng tải được).
- Python 3.12, `uv`. Dependency mới thêm vào `pyproject.toml`.
- Một phiên khác đang làm track AI & DS và sửa cùng các tệp dùng chung: `app/`, `testkit.py`,
  `pyproject.toml`, `data/download_dataset.py`. Sửa tối thiểu, đọc bản mới nhất ngay trước khi sửa,
  không format lại tệp, commit nhỏ theo từng phần.

## 4. Hạng mục

### 4.1 Module mới `00-introduction`: Giới thiệu và vòng đời Data Engineering

Đặt **đầu** danh sách module trong `track.json`. Phủ các node roadmap: What is Data Engineering?,
Data Engineering vs Data Science, Skills and Responsibilities, Data Engineering Lifecycle (Data
Generation, Data Storage, Data Ingestion, Data Serving), Choosing the Right Technologies, Data
Generation (Sources of Data: Database, APIs, Logs, Mobile Apps, IoT; Data Collection Considerations).

- Lý thuyết 5–8 phần, ≥2 mermaid (vòng đời và các "undercurrent" như security, data management,
  orchestration; bản đồ nguồn dữ liệu). Mỗi phần nối sang module sâu hơn (01–11) thay vì lặp lại.
- Bài tập là notebook trên **dữ liệu thật**, mỗi loại nguồn một bài: API công khai có phân trang và
  rate limit, log thật, dữ liệu cảm biến IoT thật, và một bài về database/CDC hoặc mobile/event nếu
  tìm được bộ phù hợp. Cộng một bài "chọn công nghệ" (ma trận quyết định, chấm bằng test cấu trúc).
  Khoảng 3 Basic, 2–3 Intermediate, 2 Advanced như các module khác.
- Milestone capstone: không thêm milestone riêng; module 00 dẫn vào M01.

### 4.2 Hybrid ingestion (Batch / Streaming / Hybrid / Realtime)

- Lý thuyết dạng `###` trong module 07 (hoặc 05 nếu hợp hơn): batch vs streaming vs hybrid, kiến
  trúc Lambda và Kappa, khi nào dùng cái nào, đối soát (reconciliation) batch với stream.
- Một bài Intermediate hoặc Advanced trên dữ liệu thật: phần stream và phần batch của cùng một
  nguồn, rồi đối soát hai kết quả. Kèm câu phỏng vấn tương ứng trong `interview.md`.

### 4.3 Các mục còn mỏng (bổ sung `###` vào module có sẵn)

| Node roadmap | Module | Bổ sung |
| --- | --- | --- |
| Java, Scala, Go | 01 | Vì sao JVM quan trọng với Spark/Kafka/Flink, khi nào gặp Scala, Go trong tooling hạ tầng |
| Data Structures and Algorithms | 01 | DSA đúng kiểu DE: hashing/partitioning, external sort, top-k bằng heap, bloom filter, HyperLogLog; thêm bài tập (Python thuần, test chấm được) |
| Cluster Computing, Distributed File Systems, Job Scheduling, Cluster Management Tools | 06 | Mở rộng phần 1–2: kiến trúc DFS, scheduler (FIFO/fair/capacity), YARN vs Kubernetes vs standalone |
| Testing: Functional, A/B, Load, Smoke | 08 | Mở rộng phần 7, thêm một bài load test (vd. API serving của module 09) |
| Monitoring: Datadog, Sentry, New Relic; CI/CD: GitLab CI, CircleCI, ArgoCD | 08 | Bảng so sánh công cụ, khi nào chọn |
| IaC: Declarative vs Imperative, Reusability, Environmental Management, Google Deployment Manager | 08 | Bổ sung lý thuyết và bảng công cụ |
| Memcached | 03 | So với Redis |
| Data Obfuscation, Metadata Management | 10 | Đặt đúng tên roadmap cho phần đã có (pseudonymization, data catalog), thêm phần còn thiếu |
| Machine Learning, MLOps (cuối roadmap) | 09 hoặc 11 | Phần "Data cho ML": training pipeline, feature store, data versioning; trỏ sang track `mlops` |

### 4.4 Dữ liệu thật

- **Capstone dùng Olist thật làm mặc định** (`data/download_olist.py`, đã tải sẵn trên máy). Sửa
  `capstone/README.md` và các milestone để lệnh mặc định là bộ thật; bộ giả lập
  (`data/generate_olist.py`) chỉ còn là phương án dự phòng và dữ liệu cho test.
- **Chỗ để dữ liệu Olist** *(quyết định của người viết thiết kế)*: bộ thật giữ nguyên ở `data/raw/`
  (đường dẫn hiện tại, track AI & DS cũng dùng). Bộ giả lập khi cần thì sinh vào
  `data/raw/olist_synthetic/` bằng tuỳ chọn `--out` sẵn có, không sửa script. Test không phụ thuộc
  dữ liệu đang có trên máy.
- **M06 (Spark) chuyển sang NYC TLC thật, 1–3 GB** (người học chốt). Capstone thành nền tảng hai
  nguồn: Olist (thương mại điện tử) và NYC TLC (vận tải). Cập nhật sơ đồ kiến trúc và tiêu chí đạt
  của M06 cho khớp.
- **M11 (cloud) dùng Olist thật** *(quyết định của người viết thiết kế)*: khoảng 120 MB, chi phí free
  tier không đáng kể.
- **Thêm notebook khám phá dữ liệu cho capstone** (đầu M01 hoặc M02): làm sạch, insight, biểu đồ, báo
  cáo trên Olist thật.
- **Bài notebook mới trên dữ liệu thật**, mỗi chủ đề một bộ khác nhau. Gợi ý (builder kiểm tra còn
  tải được, giấy phép, kích thước trước khi dùng; được thay bằng bộ tương đương):
  - Spark (06): NYC TLC Trip Record Data, chọn số tháng sao cho tổng 1–3 GB.
  - Kafka/streaming (07) và hybrid (4.2): Wikimedia EventStreams `recentchange`.
  - IoT (00): OpenAQ hoặc một bộ cảm biến công khai tương đương.
  - Log (00): log truy cập web server công khai (vd. NASA HTTP logs) hoặc tương đương.
  - API (00): một API công khai không cần key hoặc key miễn phí.
- **Mỗi bài dữ liệu thật ra đủ 4 sản phẩm ở mục 2**. Cách chấm:
  - dữ liệu sạch: test kiểm tính chất đo được (không trùng khoá, đúng kiểu, xử lý null, khoảng giá trị);
  - insight: test so số liệu với kết quả tham chiếu *(quyết định của người viết thiết kế)*: nguồn
    ghim được thì ghim mốc cố định (tháng TLC cụ thể, khoảng ngày IoT cụ thể, log tĩnh) và so với số
    tham chiếu viết sẵn; nguồn người học tự ghi (stream) thì test tính tham chiếu bằng hàm lời giải
    trên chính tệp đã ghi. Danh mục `download_dataset.py` ghi rõ mốc đã ghim;
  - biểu đồ: notebook có tạo figure (không chấm thẩm mỹ);
  - ~~báo cáo~~ đã thay bằng trắc nghiệm: `quiz.yaml` + `quiz-answers.yaml` (câu dữ liệu có đáp án cố định trên dữ liệu ghim), kiểm bằng `tests/test_quiz_files.py`; test của bài không còn chấm `report.md`.
  - Phần dùng dữ liệu thật tự skip khi bộ chưa tải; phần logic có thêm test trên fixture nhỏ để
    luôn chạy được offline.
- Dữ liệu stream trực tiếp (EventStreams) không tái lập được: notebook ghi một đoạn stream ra tệp
  trước, phân tích và chấm trên tệp đó.
- Cell đầu mỗi notebook gọi script tải: có rồi thì bỏ qua, chưa có thì tải, sau đó nạp ngay để thao
  tác. Trong lúc dựng, builder tải mỗi bộ một lần để kiểm chứng và để lại trên máy.
- Thư mục dữ liệu sạch sinh ra khi làm bài (vd. `data/clean/`) không commit.

### 4.5 App: mở notebook trong VS Code

- Màn Bài tập có nút "Mở trong VS Code" cho tệp `.ipynb` (có thể cho mọi tệp của bài). Bấm là VS Code
  mở đúng tệp. Lý do chọn VS Code thay Jupyter: người học đã làm việc trong VS Code, không cần chạy
  thêm server, VS Code tự nhận kernel `.venv`.
- Đảm bảo `ipykernel` có trong môi trường (track AI & DS có thể đã thêm).
- Sửa gọn trong màn Bài tập và API workspace, không đụng phần khác của app.

### 4.6 Capstone cuối track

- Ghi rõ trong `capstone/README.md`: bài nộp cuối là dự án hoàn chỉnh trên Olist thật, gồm pipeline
  chạy được, dữ liệu sạch, insight, **dashboard trên trình duyệt** (Metabase của M09 hoặc Streamlit),
  README portfolio. Cập nhật tiêu chí đạt của M09/M10 cho khớp.

### 4.7 Cập nhật đi kèm

- `track.json` (module 00, thứ tự), README gốc và README track (số module, số bài, sơ đồ lộ trình),
  `data/README.md` (bảng bộ dữ liệu), `setup/SETUP.md` nếu có bước mới (VS Code + Jupyter extension).

## 5. Để builder tự quyết

Tên và số lượng chính xác bài tập; chọn bộ dữ liệu cụ thể trong phạm vi gợi ý; vị trí chính xác của
từng `###` bổ sung; module đặt phần "Data cho ML"; cách hiện thực nút mở VS Code (link `vscode://`
hay gọi lệnh `code` phía server); bố cục notebook.

## 6. Kiểm chứng trước khi giao

- Mọi bài mới: starter fail/skip, `SOLUTION=1` pass (Basic/Intermediate); phần dữ liệu thật pass khi
  bộ đã tải.
- Toàn bộ test track DE vẫn pass như trước; heading `## ` của module cũ không đổi (`git diff`).
- App typecheck sạch; nút mở VS Code mở đúng tệp; module 00 hiện đúng trong app.
- Mỗi notebook mới chạy từ đầu tới cuối trên dữ liệu thật ra đủ 4 sản phẩm.
