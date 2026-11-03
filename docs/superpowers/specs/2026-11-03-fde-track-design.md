# Thiết kế: track Forward Deployed Engineer (FDE)

Ngày: 2026-11-03. Nguồn: roadmap.sh/forward-deployed-engineer (bản PDF ở `roadmap/forward-deployed-engineer.pdf`).

## 1. Mục đích và lý do

FDE là kỹ sư được "cử ra hiện trường": ngồi cạnh khách hàng, hiểu bài toán của họ, rồi **tự mang sản phẩm
của công ty vào môi trường của khách và làm cho nó chạy**, kể cả khi môi trường đó không giống máy dev: không
internet, không GPU, OS cũ, proxy công ty, không có root, dữ liệu không được rời máy. Roadmap ghi rõ FDE không
phải vai trò cho người mới; đó là full-stack engineer có thêm kỹ năng hiện trường, AI, DevOps, cloud và kỹ năng
làm việc với khách.

Người học đã học xong hoặc đang học các track DE, DA, DS, AI Engineer, MLOps, DevOps, tức là đã có phần lớn
"đồ nghề". Thứ còn thiếu, theo lời người học: **cài đặt và dựng hệ thống ở máy khách, khảo sát máy, đưa sản phẩm
của mình lên máy khách**. Track này dạy **mang đồ nghề đó ra môi trường lạ** và làm việc như một FDE senior.

**Đầu ra:** người học tự dẫn được một "hợp đồng triển khai" từ đầu đến cuối: discovery với khách, chốt scope,
khảo sát máy, đóng gói, cài lên môi trường khó (air-gapped, có GPU thật), tích hợp dữ liệu và hệ thống của khách,
chứng minh hệ thống AI không hỏng và không "bịa", xử lý sự cố, bàn giao, báo cáo ROI, phản hồi lại cho team
product. Đồng thời qua được vòng phỏng vấn FDE (DSA, System Design, decomposition, nhập vai với khách).

**Mức senior:** track phủ **kiến thức và kỹ năng** của một FDE senior. Track nói thẳng: kiến thức senior không
thay được kinh nghiệm hiện trường thật; track giúp làm việc và phỏng vấn ở mức senior, chức danh vẫn cần kinh
nghiệm bảo chứng.

Người học đọc tiếng Việt, giữ thuật ngữ tiếng Anh.

## 2. Mục tiêu, ngoài phạm vi, điều cấm

**Bốn trụ, học sâu ngang nhau (người học chốt)**
1. **Triển khai tại hiện trường:** khảo sát môi trường, đóng gói, cài đặt offline/hạn chế quyền, GPU, tích hợp,
   xử lý sự cố từ xa, nâng cấp, bàn giao. Đây là trụ người học quan tâm nhất và là xương sống của track.
2. **Làm việc với khách:** requirements gathering, discovery & scoping, technical scoping & sequencing, trade-off
   scope/speed/quality, enterprise workflow, ROI & AI impact, stakeholder management, technical writing, product
   feedback loop.
3. **DSA và System Design** ở mức phỏng vấn senior (roadmap: "DSA is the first gate in FDE interviews").
4. **Cloud và IaC**, chia làm hai mục:
   - **Phần miễn phí** trong track chính: giả lập trên laptop (LocalStack, kind/k3d, máy ảo).
   - **Mục "Cloud lab (có phí)"** tách riêng, viết sẵn đầy đủ để người học làm khi có điều kiện (mục 4.3).

**"Sản phẩm công ty" (người học chốt):** một hệ thống AI hoàn chỉnh gồm web app full-stack, data pipeline nạp
tài liệu/dữ liệu của khách và ứng dụng LLM/RAG chạy model local. Track cấp sẵn sản phẩm này (mục 6). Người học
không xây nó từ đầu mà đóng gói, cài đặt, tuỳ biến, sửa và vận hành nó tại "máy khách", đúng như việc FDE làm
với sản phẩm của công ty mình.

**Máy khách giả lập (Claude chọn, người học đồng ý):** mỗi "khách" là một **VM QEMU/KVM** trên laptop, SSH vào
được, mỗi máy có "tật" riêng (mục 5). Không dùng container giả làm máy khách cho các bài cài đặt.
**PC RTX 3060 của người học** đóng vai "khách hàng có GPU thật" trong vài bài **tuỳ chọn**.

**Ba anti-goal người học quan tâm nhất (ưu tiên hàng đầu khi builder phải đánh đổi)**
- **Không có "happy path" giả.** Mỗi bài cài đặt/triển khai có **ít nhất một chỗ hỏng thật** do môi trường gây
  ra (không phải lỗi chính tả cài sẵn trong code): proxy chặn, cert công ty, glibc cũ, đĩa đầy, port bị chặn,
  SELinux, driver không khớp CUDA… Người học phải chẩn đoán rồi mới qua được.
- **Kỹ năng mềm không thành lý thuyết suông.** Mỗi module của trụ 2 bắt người học **viết ra tài liệu thật**
  (scoping doc, SOW, email báo tin xấu, status update, runbook, báo cáo ROI, product feedback) và tài liệu đó
  **được chấm**: phần có cấu trúc chấm bằng test, phần lập luận chấm bằng rubric và LLM-judge local.
- **Ra được portfolio và phỏng vấn.** Capstone là một repo khoe được (mục 7). Có bộ câu hỏi và bài luyện riêng
  cho vòng phỏng vấn FDE: DSA, System Design, decomposition interview, nhập vai với khách, take-home.

**Các điều cấm khác (làm vậy là hỏng dù chạy được)**
- **Lặp lại track cũ.** Docker, RAG, Terraform, K8s, Linux cơ bản, observability đã dạy ở DevOps/AE/MLOps/DE thì
  chỉ ôn nhanh (tối đa một heading `## ` mỗi chủ đề, có link về module gốc). Bài tập phải khác bài các track đó
  và tập trung vào môi trường lạ, khách hàng, ràng buộc.
- **Bài bắt buộc cần thứ người học chưa có**: cloud trả phí, PC, API key trả phí, tài khoản bên ngoài. Bài cần
  PC hoặc cloud là tuỳ chọn và tự skip.
- Test chỉ grep chuỗi trong khi chạy được công cụ thật. Test phụ thuộc mạng/dịch vụ chưa bật mà không tự skip.
- Phá vỡ track khác hoặc app hiện có.

**Ngoài phạm vi**
- Frontend/Backend dạy từ đầu (roadmap trỏ sang roadmap Frontend/Backend riêng). Track chỉ dạy **prototyping
  full-stack nhanh cho khách** dựa trên stack sẵn có của sản phẩm.
- Sales, pricing hợp đồng, luật hợp đồng. Chỉ dạy phần kỹ thuật của SOW/scope.
- Huấn luyện model. Model dùng sẵn qua Ollama.

## 3. Ràng buộc

- Cấu trúc thư mục, frontmatter, interview, quiz, capstone: đúng `CONTENT_SPEC.md`. Track id: `fde`.
- **App chỉ được sửa một chỗ nhỏ, kiểu thêm vào:** hiện mục "Cloud lab (có phí)" tách riêng khỏi danh sách module
  chính (vd. trường tuỳ chọn trên module trong `track.json` như `"section": "cloud-lab"`, app gom các module đó
  thành nhóm riêng có nhãn "Có phí", không tính vào tiến độ chính hoặc tính riêng). Track khác không cần đổi gì.
  Có test cho phần app thay đổi. Cách làm cụ thể: builder quyết.
- Mỗi module: 5–8 phần lý thuyết (`## `), ≥2 sơ đồ mermaid, phần cuối là tài liệu tham khảo. Module dùng công cụ
  lần đầu có `## 0. Cài đặt` theo quy ước của DevOps/MLOps (bảng phiên bản đã kiểm, checksum, cách gỡ, không
  `curl | sudo bash`).
- `interview.md` ≥12 câu mỗi module, có câu tình huống hiện trường ("khách nói X, bạn làm gì").
- Khoảng 7 bài mỗi module (3 Basic, 2–3 Intermediate, 2 Advanced); module DSA nhiều bài hơn (mục 4.1). Starter
  chạy test phải fail hoặc skip, không lỗi cú pháp. `SOLUTION=1` pass với Basic và Intermediate. Advanced có
  `SOLUTION.md` (hướng làm + rubric).
- Python 3.12, `uv`. Code không có comment inline; docstring chỉ khi thật cần.
- **Máy:** laptop 16 core, 31 GB RAM (khi đang dùng còn trống ~13 GB), 176 GB đĩa trống, RTX 3050 4 GB, có
  `/dev/kvm` và `qemu-system-x86_64`, có `kind`. Mỗi bài chạy tối đa **2 VM cùng lúc** (capstone tối đa 3).
  VM phụ (proxy, registry, Keycloak, file share) ≤2 GB; **VM chạy sản phẩm ≤5 GB**; tổng RAM VM trong một bài
  ≤8 GB. Ollama local đã có `qwen2.5:3b/7b`, `bge-m3`, `nomic-embed-text`.
- **LLM chạy ngay trong VM khách**, không gọi Ollama của host (giữ đúng bài học air-gapped/data residency). Model
  mặc định là model nhỏ quantized (cỡ 0.5–1.5B, builder đo và chọn) cùng embedding nhỏ, **đóng sẵn trong bundle
  offline**; model lớn hơn chỉ ở bài GPU (laptop 3050 hoặc PC 3060).
- **Thời gian chạy test:** nút "Run tests" của app cắt pytest sau 300 s (`app/server/workspace.ts`). Bài VM nhắm
  ≤5 phút nhờ **snapshot VM nối tiếp** (boot từ snapshot đã chuẩn bị, capstone milestone bắt đầu từ snapshot "sau
  milestone trước" do `fdekit` dựng từ lời giải tham chiếu). Bài nào vẫn vượt 5 phút thì README ghi rõ chạy bằng
  terminal (`run:`); không sửa timeout của app.
- **Runtime container ở máy khách:** IT khách đã cài sẵn theo hồ sơ (ngân hàng: Podman rootless; công ty luật: k3s;
  các khách khác: Docker hoặc Podman). Người học không phải cài runtime khi không có root. Riêng cách cài **không
  container** (`$HOME` + `systemd --user`, wheelhouse + binary) là một bài Advanced ở module 04, không phải đường
  đóng gói chính của sản phẩm.
- **Không đụng hạ tầng dùng chung track khác đang sửa.** DevOps làm ở máy khác; MLOps Phase 3 đang chạy ở các
  worktree khác. Vì vậy:
  - Helper riêng `fdekit.py` ở gốc repo (có test trong `tests/`). Không sửa `testkit.py`, `mlopskit.py`,
    `llmkit.py`; chỉ **dùng** helper sẵn có (`DockerLab`, `require_tool`, `run_sandboxed`, `llmkit.get_client`…).
  - Hạ tầng ở `setup/fde/`, cổng riêng không trùng các stack khác, remap được qua `setup/.env`.
  - `CONTENT_SPEC.md`: chỉ **thêm** mục "Track FDE" ở cuối. `data/download_dataset.py`, `data/README.md`: chỉ
    thêm entry mới.
  - Dependency Python mới vào môi trường mặc định, không hạ pin hiện có; xung đột thì chạy trong container
    (bài học MLOps: kiểm import được dưới pin pandas hiện tại trước khi thêm).
  - Validator `tests/test_fde_track.py` theo mẫu `tests/test_mlops_track.py`.
- Làm trong worktree `../DataScience-fde`, nhánh `fde-track`. Rebase lên `origin/main` trước khi mở PR.
- **Các bài học quy trình từ MLOps** (đưa vào mọi brief): quote giá trị `text` trong quiz; mọi quy tắc test chấm
  phải được nói trong README/milestone; bài sự cố: README chỉ tả triệu chứng, tên hàm/API trong starter không
  lộ nguyên nhân; không gọi `docker` trần; không xoá tài nguyên chỉ theo nhãn dùng chung (agent song song xoá
  nhầm của nhau); ngưỡng thời gian chừa gấp đôi; chấm bằng công cụ thật, không mô phỏng bằng Python.

## 4. Danh sách module

### 4.1 Track chính (miễn phí)

| # | id | Module | Nội dung chính |
| --- | --- | --- | --- |
| 00 | `00-introduction` | FDE là gì | Nguồn gốc (Palantir "Delta/Echo"), FDE ở các công ty AI hiện nay; khác Solutions Engineer / Sales Engineer / Consultant / SWE; một tuần làm việc của FDE; **bản đồ đồ nghề đã học** ở các track khác (link); giới thiệu "sản phẩm công ty" và các "khách hàng" của track; vòng phỏng vấn FDE |
| 01 | `01-site-survey` | Khảo sát môi trường khách | Checklist trước khi đến; đọc hệ thống lạ: OS/kernel/glibc, CPU/RAM/disk/inode, GPU/driver, mạng (DNS, route, proxy, MTU, port ra/vào), thời gian/NTP, SELinux/AppArmor, ulimit, user/quyền; **viết script site-survey** chạy không cần root, xuất báo cáo JSON + Markdown; so với yêu cầu tối thiểu của sản phẩm (preflight) |
| 02 | `02-packaging-delivery` | Đóng gói cho môi trường lạ | Bundle cài được ở mọi nơi: image tarball (`docker save`/OCI layout), wheelhouse offline (`uv`), binary tĩnh, model weights; **installer idempotent** có preflight, rollback, log; versioning và tương thích ngược; SBOM, checksum, ký bundle (cosign); cấu hình theo khách (values/profile) |
| 03 | `03-airgapped-proxy` | Air-gapped, proxy và cert công ty | Cài không có internet: registry nội bộ, mirror apt/dnf/pip, chuyển bundle qua "USB" (ổ ảo); **proxy công ty** (HTTP(S)_PROXY, NO_PROXY, proxy cho Docker daemon), **TLS inspection** và CA nội bộ (trust store hệ thống, Python, Node, container); kiểm tra toàn vẹn khi chuyển |
| 04 | `04-restricted-hosts` | Máy bị khoá và máy cũ | Không có root: rootless Podman/Docker, `systemd --user`, cài vào `$HOME`; SELinux enforcing (context, boolean), firewall (firewalld/nftables); OS cũ (RHEL/Rocky 8, Ubuntu 20.04): glibc, Python hệ thống, container cũ; đĩa gần đầy, `/tmp` noexec, giới hạn ulimit; Windows/WSL ở mức nhận biết |
| 05 | `05-gpu-field` | GPU ở máy khách | Ma trận driver ↔ CUDA ↔ container toolkit; chẩn đoán `nvidia-smi`, CDI; định cỡ LLM theo VRAM (quantization, context length, batch), **fallback CPU**; benchmark và báo cáo năng lực phần cứng cho khách; vLLM/llama.cpp/Ollama so sánh khi triển khai on-prem. Bài trên PC 3060 là tuỳ chọn, có đường laptop 3050/CPU |
| 06 | `06-k8s-at-customer` | Cài lên Kubernetes của khách | Khách đã có cluster và bạn **không có cluster-admin**: namespace-scoped install, Helm chart của sản phẩm (values theo khách), image từ registry nội bộ, PSA/securityContext, quota, NetworkPolicy chặn sẵn; **k3s air-gapped** khi khách chưa có cluster; OpenShift ở mức khác biệt cần biết. K8s cơ bản trỏ về DevOps 10–12 |
| 07 | `07-customer-integration` | Tích hợp hệ thống và dữ liệu của khách | SSO (OIDC/SAML qua Keycloak, LDAP/AD); kết nối nguồn dữ liệu khách (DB, file share SMB/NFS, S3-compatible, export từ hệ thống cũ) mà **dữ liệu không rời máy**; connector tuỳ biến; secret theo chính sách khách (Vault/file/env); **security questionnaire** và review bảo mật của khách; data residency, PII |
| 08 | `08-field-troubleshooting` | Xử lý sự cố tại hiện trường | Quy trình chẩn đoán có hệ thống khi **chỉ có quyền hạn chế** (khách gõ lệnh qua screen-share, chỉ đọc log được gửi lại); journalctl, `ss`, `strace`, `tcpdump`, `curl -v`, `openssl s_client`, DNS; **support bundle** (script thu log/config đã che secret); tái hiện lỗi của khách ở lab; escalation sang team product với bằng chứng |
| 09 | `09-production-trust` | Chứng minh hệ thống không hỏng, không "bịa" | Roadmap: "proving to customers that what they built won't break or go rogue". Eval suite trên **dữ liệu của khách** (groundedness, citation, refusal), guardrails, red-team cơ bản (prompt injection qua tài liệu), giám sát đã ship cùng sản phẩm, backup/restore, **nâng cấp tại chỗ và rollback**, SLA/SLO thực tế cho on-prem; acceptance test cùng khách. Eval/LLM-judge cơ bản trỏ về AE 20 |
| 10 | `10-rapid-prototyping` | Prototype full-stack nhanh cho khách | Tuỳ biến sản phẩm theo workflow của khách trong vài ngày: thêm màn hình/endpoint, connector, prompt và retrieval theo domain; demo-driven development; "throwaway vs productize"; giữ fork tối thiểu và đẩy thay đổi chung về product; feature flag theo khách |
| 11 | `11-discovery-requirements` | Discovery và requirements gathering | Phỏng vấn discovery (câu hỏi mở, "5 whys", quan sát workflow thật), **enterprise workflow mapping** (as-is/to-be, ai làm gì, hệ thống nào), tách yêu cầu thật khỏi giải pháp khách tự nghĩ ra, ràng buộc ẩn (bảo mật, mua sắm, IT); **stakeholder simulator**: LLM local đóng vai khách có yêu cầu ẩn, người học phải hỏi ra |
| 12 | `12-scoping-sequencing` | Scoping, sequencing và trade-off | Technical scoping, chia giai đoạn (pilot → production), sequencing theo rủi ro và phụ thuộc, ước lượng có khoảng tin cậy; **scope/speed/quality** và nói "không"; MoSCoW; SOW phần kỹ thuật, tiêu chí nghiệm thu; change request khi scope trôi |
| 13 | `13-business-roi` | Business acumen, ROI & AI impact | Hiểu khách kiếm tiền và tốn tiền ở đâu; đo baseline trước khi triển khai; **mô hình ROI** (giờ công tiết kiệm, lỗi giảm, chi phí GPU/hạ tầng/vận hành), TCO on-prem vs cloud; đo AI impact sau triển khai; trình bày cho CFO/CTO |
| 14 | `14-communication-stakeholders` | Giao tiếp, stakeholder và feedback loop | Bản đồ stakeholder (sponsor, user, IT, security, procurement); status update, **báo tin xấu**, escalation; technical writing: design doc, runbook, README bàn giao, exec summary; demo cho khách; **product feedback loop**: viết feedback có bằng chứng, ưu tiên hoá, đóng vòng với khách |
| 15 | `15-dsa-core` | DSA I: nền tảng phỏng vấn | Big-O; arrays/strings, hashing, two pointers, sliding window, stack/queue, binary search, linked list, intervals, prefix sum; **~25 bài** chấm bằng test (có test hiệu năng chặn lời giải sai độ phức tạp) |
| 16 | `16-dsa-advanced` | DSA II: cây, đồ thị, DP | Tree/BST, heap, graph (BFS/DFS, topo sort, Dijkstra, union-find), trie, backtracking, DP (1D/2D/knapsack/interval), greedy; **~25 bài**; bài "đề thực tế" kiểu FDE (parse log, gộp sự kiện, lịch phụ thuộc) |
| 17 | `17-system-design-core` | System Design I | Khung trả lời; ước lượng; cache, queue, DB/sharding/replication, consistency, rate limit, idempotency; các đề kinh điển; ôn từ DevOps/DE có link |
| 18 | `18-system-design-fde` | System Design II: thiết kế cho khách | Thiết kế **bị ràng buộc bởi khách**: on-prem/hybrid/BYOC, multi-tenant vs single-tenant per customer, air-gapped update channel, RAG trên tài liệu có phân quyền, inference GPU dùng chung, data residency; bộ đề mức senior có rubric |
| 19 | `19-cloud-iac` | Cloud & IaC cho FDE (miễn phí) | Mô hình triển khai vào **tài khoản cloud của khách** (BYOC): cross-account IAM role, VPC/subnet/private endpoint, peering, KMS; **Terraform với LocalStack**, module tái dùng theo khách, state và quyền; Terraform cơ bản trỏ về DevOps 08 |
| 20 | `20-fde-interview` | Vòng phỏng vấn FDE | Cấu trúc vòng phỏng vấn FDE; **decomposition interview** (bài toán mơ hồ → kế hoạch); nhập vai khách (với stakeholder simulator); behavioral (STAR, câu chuyện hiện trường); take-home; tổng hợp portfolio từ capstone |

Module 15–16 không phụ thuộc module trước; README track ghi rõ **có thể học song song từ đầu** (mỗi tuần vài bài).
Topic con và tên bài: builder quyết, miễn phủ đủ nội dung trên.

### 4.2 Đối chiếu roadmap PDF

| Mục roadmap | Ở đâu |
| --- | --- |
| Introduction, Roles & Responsibilities | 00 |
| Frontend / Backend skills (full apps cho khách) | 10 (+ sản phẩm cấp sẵn), trỏ về roadmap ngoài |
| Linux skills | 01, 04, 08 (trỏ về DevOps 01) |
| DSA & System Design | 15–18, 20 |
| AI Engineering skills | 05, 09, 10 (trỏ về AE) |
| DevOps skills, cloud platform, IaC | 02, 03, 06, 19, Cloud lab |
| "Won't break or go rogue in production" | 09 |
| Requirements Gathering, Discovery & Scoping | 11 |
| Technical Scoping & Sequencing, Trade-offs | 12 |
| Business Acumen, ROI & AI Impact, Enterprise Workflow | 11, 13 |
| Communication, Technical Writing, Stakeholder Mgmt, Product Feedback Loop | 14 |

### 4.3 Mục "Cloud lab (có phí)"

Tách riêng trong app (mục 3). Viết sẵn đầy đủ (lý thuyết, bài, lời giải), mọi test tự skip khi không có credential.
Mỗi bài ghi **chi phí ước tính**, dùng free tier khi có, có **budget alarm** dựng trước tiên và bước **`destroy`
bắt buộc** kèm script kiểm không còn tài nguyên tính phí.

| # | id | Lab | Nội dung |
| --- | --- | --- | --- |
| C1 | `c1-aws-byoc` | Triển khai vào tài khoản AWS "của khách" | Hai account (vendor + customer, dùng AWS Organizations hoặc hai account free tier); cross-account role; Terraform dựng VPC private + EC2/ECS; sản phẩm chạy không có public IP, truy cập qua SSM |
| C2 | `c2-gcp-azure` | Cùng bài trên GCP hoặc Azure | Khác biệt IAM/networking cần biết khi khách dùng cloud khác |
| C3 | `c3-cloud-gpu-inference` | GPU trên cloud cho khách | Thuê GPU theo giờ (spot), deploy LLM serving, đo chi phí/token so với on-prem, tắt tự động |

Thiếu credential thì đây chỉ là tài liệu đọc; không bài nào của track chính phụ thuộc mục này.

## 5. Môi trường thực hành: VM "khách hàng"

**Helper `fdekit.py`** (có test): builder quyết API, tối thiểu cần:
- Dựng VM từ **cloud image chính thức** (tải một lần, kiểm sha256, cache trong `data/raw/`) bằng QEMU/KVM +
  cloud-init; overlay qcow2 để **reset về trạng thái sạch** trong vài giây; SSH bằng key sinh riêng cho lab.
- Áp **"hồ sơ khách"** lên VM bằng cloud-init/script: chặn egress (chỉ còn đường qua proxy hoặc không gì cả),
  proxy có TLS inspection với CA riêng, user không sudo, SELinux enforcing, đĩa nhỏ, OS cũ, DNS nội bộ…
- Mạng lab tách biệt (user-mode hoặc bridge riêng), chỉ bind `127.0.0.1` phía host; không đụng mạng thật của máy.
- Gate: skip khi không có `/dev/kvm`, thiếu image, thiếu RAM. Dọn VM theo id riêng của lần chạy (bài học MLOps).
- Gate PC GPU: skip khi biến môi trường cấu hình SSH tới PC chưa có. Đến bài cần PC thì **dừng, hướng dẫn người
  học bật SSH và tạo user lab** (theo memory: không tự truy cập PC).

**Danh mục khách gợi ý** (builder có thể đổi, giữ đa dạng):

| Khách (hư cấu) | Máy | "Tật" chính |
| --- | --- | --- |
| Ngân hàng | Rocky/RHEL-compatible 8 | air-gapped hoàn toàn, SELinux enforcing, không root |
| Bệnh viện | Ubuntu 20.04 cũ | proxy có TLS inspection, CA nội bộ, đĩa nhỏ |
| Nhà máy | Debian, ít RAM | không GPU, mạng chập chờn, phải chạy CPU |
| Công ty luật (capstone) | Ubuntu 22.04 + K8s (k3s) do IT khách quản | namespace-scoped, registry nội bộ, cần GPU (PC tuỳ chọn) |

**Chỗ hỏng thật** (anti-goal "không happy path"): mỗi bài cài đặt sinh ra ít nhất một lỗi từ chính hồ sơ khách,
không phải từ code cố tình hỏng. README chỉ mô tả bối cảnh và triệu chứng, nguyên nhân chỉ có trong `solutions/`.
Test kiểm **kết quả cuối trên VM** (dịch vụ trả lời đúng qua SSH tunnel, installer chạy lại idempotent, báo cáo
survey khớp thực tế VM).

## 6. "Sản phẩm công ty"

Track cấp sẵn một sản phẩm AI hư cấu (tên: builder đặt, không trùng thương hiệu có thật) trong
`tracks/fde/product/`, có **nhiều version phát hành** (vd. v1.0, v1.1 có migration DB) để có bài nâng cấp/rollback.

- **Web app:** frontend nhẹ + backend FastAPI, đăng nhập (local + OIDC), phân quyền theo nhóm tài liệu.
- **Data pipeline:** worker nạp tài liệu (PDF/DOCX/HTML) và dữ liệu có cấu trúc từ nguồn của khách, chunk, embed.
- **LLM/RAG:** Postgres + pgvector, LLM và embedding qua **Ollama** (model nhỏ mặc định, model lớn khi có GPU),
  trả lời có trích dẫn, có eval harness và metric.
- **Vận hành:** healthcheck, metrics, log có cấu trúc, script backup/restore, support bundle.
- Có cả Compose bundle và Helm chart. Kích thước bundle offline giữ ở mức hợp lý cho laptop (builder đo và ghi).

Sản phẩm là **công cụ của bài**, không phải chủ đề dạy: người học không phải đọc hết code, nhưng code phải sạch
để làm bài tuỳ biến (module 10) và chẩn đoán (module 08). Sản phẩm có test riêng.

## 7. Capstone: triển khai trợ lý hợp đồng cho một công ty luật

**Khách (hư cấu):** phòng pháp chế của một tập đoàn muốn trợ lý AI tra cứu và rà soát hợp đồng. Hợp đồng là dữ
liệu mật, **không được rời khỏi máy chủ của khách**, IT khách quản K8s và chặn internet.

**Dữ liệu thật:** **CUAD** (Contract Understanding Atticus Dataset, ~510 hợp đồng thật, nhãn chuyên gia cho 41 loại
điều khoản, CC BY 4.0). Nhãn chuyên gia dùng để dựng eval "có tìm đúng điều khoản không, có bịa không". Builder kiểm
nguồn tải, license và sha256, thêm entry vào `data/download_dataset.py`.

**Milestone** (test `test_mNN_*`; `SOLUTION=1` chấm `capstone/solutions/project/`). Mỗi milestone sau một module:

| M | Sau module | Nội dung |
| --- | --- | --- |
| m01 | 01 | Khảo sát VM của khách bằng script site-survey; báo cáo khoảng cách so với yêu cầu sản phẩm |
| m02 | 02 | Bundle offline cho đúng khách này, installer có preflight dựa trên báo cáo m01 |
| m03 | 03 | Cài qua môi trường air-gapped + registry nội bộ; xác minh toàn vẹn bundle |
| m04 | 04 | Chạy dưới ràng buộc bảo mật của khách (không root, SELinux) |
| m05 | 05 | Định cỡ model theo phần cứng; CPU fallback; (tuỳ chọn) chạy trên PC GPU |
| m06 | 06 | Cài bằng Helm vào namespace k3s của khách, không cluster-admin |
| m07 | 07 | SSO qua Keycloak của khách; nạp CUAD qua connector từ "file share" của khách; phân quyền tài liệu |
| m08 | 08 | Sự cố dựng sẵn ở hiện trường; chẩn đoán chỉ qua support bundle và lệnh "nhờ khách gõ"; báo cáo sự cố |
| m09 | 09 | Eval suite trên nhãn CUAD + red-team prompt injection; nâng cấp v1.0 → v1.1 tại chỗ và rollback; acceptance test |
| m10 | 10 | Tuỳ biến cho workflow pháp chế (vd. bảng rà soát điều khoản rủi ro), giữ fork tối thiểu |
| m11 | 11 | Discovery với stakeholder simulator → tài liệu yêu cầu (chấm theo yêu cầu ẩn hỏi ra được) |
| m12 | 12 | Scoping doc + kế hoạch pilot → production + tiêu chí nghiệm thu |
| m13 | 13 | Báo cáo ROI dựa trên số đo thật từ m09 (thời gian rà soát, độ chính xác) |
| m14 | 14 | Gói bàn giao: runbook, README vận hành, exec summary, product feedback gửi team product |
| m15 | 18 | Design doc: mở rộng cho 5 công ty con (multi-site, cập nhật air-gapped, GPU dùng chung) |
| m16 | 20 | Đánh giá độc lập mức senior: khách mới với hồ sơ máy lạ, người học tự đi trọn vòng (survey → cài → sự cố → bàn giao) theo rubric; repo capstone hoàn chỉnh làm portfolio |

**Capstone là một dự án riêng ngoài repo học (người học chốt):** repo học này **chỉ chứa đề và hướng dẫn** của
capstone. Người học làm capstone trong **một repo Git riêng** do chính họ tạo (vd. `~/projects/<tên-dự-án>`), như một
dự án setup thật, đẩy lên GitHub public để làm portfolio.
- Milestone đầu tiên (m00, trước m01) hướng dẫn tạo repo riêng: cấu trúc thư mục đề xuất, `Makefile`/`justfile`,
  README case study, license, `.gitignore` chặn secret/key lab/dữ liệu. Repo riêng **tự chứa**: phần lab nó cần (dựng
  VM, hồ sơ khách) và bản phát hành của sản phẩm được lấy về theo hướng dẫn (bundle phát hành từ repo học, có
  checksum), không import code từ repo học khi chạy.
- **Bộ chấm ở repo học** trỏ vào repo riêng qua biến môi trường (vd. `FDE_CAPSTONE_DIR`), tự skip khi chưa đặt.
  Test kiểm hành vi thật (VM, dịch vụ, tài liệu có frontmatter) như mục 8, cộng kiểm repo riêng không phụ thuộc repo
  học và không lọt secret.
- **Lời giải tham chiếu** vẫn cần để builder kiểm bộ chấm (`SOLUTION=1`). Nó nằm ở `capstone/solutions/` như các track
  khác, dạng hướng dẫn và dự án mẫu; người học không copy nó sang repo riêng.
- **License:** sản phẩm hư cấu phát hành MIT để người học được đưa bundle vào repo public; CUAD **không đưa vào repo**,
  chỉ có script tải kèm ghi công đúng yêu cầu CC BY 4.0.
- Đẩy lên GitHub là người học tự làm (track chỉ hướng dẫn).

Thứ tự milestone tuần tự theo hợp đồng thật. Builder có thể đổi thứ tự trụ 2 (11–14) lên trước nếu thấy hợp lý
hơn về sư phạm (discovery thường xảy ra trước khi cài), miễn ghi lý do.

## 8. Dạng bài và cách chấm

`pytest` là bộ chấm duy nhất; test gọi công cụ thật và tự skip khi thiếu KVM, image, Ollama, PC, credential.

- **Bài hiện trường (VM):** người học viết script/cấu hình/installer, test dựng VM với hồ sơ khách, chạy bài của
  người học qua SSH, kiểm kết quả cuối (dịch vụ trả lời, idempotent, báo cáo đúng). Thời gian mỗi bài mục tiêu
  ≤10 phút kể cả boot VM (không kể tải image lần đầu); builder đo và chỉnh.
- **Bài code:** Python có tên cố định trong `starter/`, như các track khác.
- **Bài DSA:** hàm có signature cố định, test đúng sai + test hiệu năng (input lớn với giới hạn thời gian có
  dư gấp đôi) để chặn lời giải sai độ phức tạp.
- **Bài tài liệu (trụ 2, System Design):** người học nộp tệp Markdown có **frontmatter YAML bắt buộc** (vd. danh
  sách scope must/should/won't, ước lượng có min/max, rủi ro, tiêu chí nghiệm thu, con số ROI). Test kiểm phần có
  cấu trúc một cách xác định (đủ trường, số liệu nhất quán, ROI tính đúng từ input). Phần lập luận chấm bằng
  **LLM-judge qua `llmkit`** (Ollama local) theo rubric công khai trong README; test judge tự skip khi không có
  Ollama và có ngưỡng chừa biên. Rubric đầy đủ + bài mẫu trong `solutions/`.
- **Stakeholder simulator:** LLM local đóng vai khách theo persona có **yêu cầu ẩn**; người học hỏi qua CLI, transcript
  được lưu; tài liệu yêu cầu được chấm theo số yêu cầu ẩn phát hiện được. Persona và yêu cầu ẩn chỉ nằm trong
  `solutions/` (hoặc được mã hoá nhẹ để không lộ khi đọc lướt).
- **Quiz `knowledge`** cho câu chọn công cụ/tình huống.

## 9. Thứ tự làm (gợi ý cho plan)

- **Phase 1:** hạ tầng (`fdekit.py` + VM lab, sản phẩm v1.0 + v1.1, `setup/fde/`, entry dữ liệu CUAD và cloud image,
  thay đổi app cho mục Cloud lab, `track.json` với `status: active`, README track, mục "Track FDE" trong
  `CONTENT_SPEC.md`, validator), module 00–03, m00–m03.
- **Phase 2:** module 04–10, m04–m10.
- **Phase 3:** module 11–14 (trụ 2), m11–m14.
- **Phase 4:** module 15–20, Cloud lab C1–C3, m15–m16.

Subagent-driven, implementer và reviewer độc lập mỗi task, review toàn nhánh cuối mỗi phase; làm liên tục hết track,
chỉ dừng khi cần người học (PC, credential cloud, merge/push).

## 10. Quyết định của Claude (người học chưa duyệt từng điểm)

1. Track id `fde`, 21 module (00–20) + 3 Cloud lab, ~150 bài, 16 milestone.
2. VM QEMU/KVM + cloud-init làm máy khách; tối đa 2 VM mỗi bài (3 ở capstone).
3. Capstone dùng CUAD (công ty luật) vì là dữ liệu thật, có license mở, có nhãn chuyên gia để dựng eval chống "bịa".
4. Kỹ năng mềm chấm bằng frontmatter có cấu trúc (xác định) + LLM-judge local (tự skip).
5. Stakeholder simulator bằng LLM local cho discovery và phỏng vấn nhập vai.
6. Sản phẩm dùng Postgres + pgvector + Ollama + FastAPI, có Compose và Helm, hai version để dạy nâng cấp.
7. Cloud lab nhắm AWS trước (C1), GCP/Azure sau (C2).
8. DSA ~50 bài trong hai module, học song song từ đầu được.
12. Capstone làm trong repo riêng của người học; repo học chấm qua `FDE_CAPSTONE_DIR`, lời giải mẫu vẫn ở `capstone/solutions/`.
9. LLM chạy trong VM khách với model nhỏ đóng trong bundle; VM sản phẩm ≤5 GB, tổng ≤8 GB mỗi bài.
10. Giữ timeout 5 phút của app; dùng snapshot VM nối tiếp, bài quá dài chạy bằng terminal.
11. Runtime container do IT khách cài sẵn; cài không container chỉ là bài Advanced module 04.

## 11. Để builder quyết

- Phiên bản cụ thể mọi công cụ, distro và cloud image (bản ổn định, ghi vào `## 0. Cài đặt`).
- API của `fdekit.py`, cách mô phỏng proxy TLS inspection, mạng lab.
- Tên sản phẩm, frontend stack nhẹ nhất đủ dùng, cấu trúc code sản phẩm.
- Cổng của `setup/fde/`, model Ollama mặc định cho judge và simulator.
- Cách hiện mục Cloud lab trong app (miễn tách riêng, có nhãn có phí, không phá track khác).
- Tên và số lượng bài trong từng module, miễn đủ nội dung mục 4.
