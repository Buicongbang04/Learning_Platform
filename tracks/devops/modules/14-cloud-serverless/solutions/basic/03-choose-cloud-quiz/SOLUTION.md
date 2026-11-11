# Lời giải: trắc nghiệm chọn nhà cung cấp cloud và nền tảng serverless

| Câu | Đáp án | Giải thích ngắn |
| --- | --- | --- |
| edge-latency | b | Logic nhỏ, cần chạy sát người dùng ở nhiều châu lục, khởi động tức thì: Cloudflare Workers chạy trên isolate V8 ở mọi PoP, không có cold start kiểu container. Lambda ở một region vẫn xa người dùng các châu khác; provisioned concurrency chỉ bỏ cold start, không bỏ khoảng cách. Một VM ở Đức có CDN vẫn phải đi về Đức cho mọi request động |
| preview-per-pr | a | Next.js, preview cho mỗi PR, không ai làm hạ tầng: đúng thế mạnh của Vercel (cũng là nơi phát triển Next.js). Kubernetes với ApplicationSet làm được nhưng là cả một nền tảng phải vận hành cho 4 người frontend |
| marketing-site | a | Site tĩnh từ git, form, redirect, function nhỏ, lưu lượng thấp: Netlify có sẵn cả bốn, gói miễn phí đủ. RDS, GKE, Heroku dyno chạy cả ngày là tiền cố định cho một trang tĩnh |
| microsoft-shop | b | Danh tính (Entra ID), code (.NET), hợp đồng đều ở Microsoft: Azure Functions với Blob trigger và managed identity không cần credential nào. Đồng bộ người dùng sang IAM user từng người là tạo thêm credential dài hạn |
| bigquery-team | c | Dữ liệu và trigger đã ở GCP: Cloud Run functions (tên mới của Cloud Functions thế hệ 2) nhận event từ Cloud Storage qua Eventarc. Service account key dài hạn trong biến môi trường là thứ cần tránh; cron trên laptop không phải hạ tầng |
| steady-eu-vm | d | Tải đều 24/7, có người vận hành Linux, ưu tiên giá: VM ở Hetzner rẻ hơn nhiều lần so với Lambda có provisioned concurrency cả ngày (trả tiền cho cả thời gian chờ) hay dyno của Heroku. Serverless đắt lên khi tải đều và cao |
| hobby-vps | a | Nhiều RAM nhất mỗi đồng, không cần SLA: Contabo. Đổi lại hỗ trợ chậm, mạng và ổ đĩa không đều; không hợp cho production quan trọng. EC2 r7i.2xlarge đắt hơn nhiều; Netlify Functions không chạy được kind |
| one-day-prototype | b | Git push là chạy, add-on cho Postgres và Redis, không ai biết hạ tầng: Heroku. Đắt hơn khi lớn, nhưng một ngày làm demo thì không phương án nào nhanh bằng. Workers không chạy Rails |
| china-market | c | Hạ tầng trong Trung Quốc đại lục cần ICP, và kết nối xuyên biên giới chậm, không ổn định: Alibaba Cloud có nhiều region trong nước, hỗ trợ thủ tục ICP, CDN trong nước. Singapore hay Tokyo vẫn ở ngoài |
| long-job | d | Lambda có timeout tối đa 900 giây (15 phút); không đặt được 3600. Job 40 phút chạy dạng container (ECS/Fargate task do EventBridge Scheduler bật, Cloud Run job, Kubernetes Job). Chuỗi Lambda gọi đồng bộ nhau trả tiền cho cả thời gian chờ và vẫn vướng timeout |
| fan-out | b | Ba consumer độc lập cần cùng một event: fan-out bằng EventBridge rule (hay SNS) vào ba hàng đợi, mỗi hàng đợi có retry và DLQ riêng. Một hàng đợi chung chia message cho các consumer (mỗi message chỉ một service nhận); gọi đồng bộ làm khách chịu lỗi của email |
| partner-api | c | API key theo đối tác, quota theo ngày, kiểm schema: API Gateway REST API (usage plan, API key, request validator). HTTP API rẻ hơn nhưng không có usage plan và API key; Function URL không có cả hai |
| lambda-customer-duties | a, b, c | Lambda là managed: AWS lo hạ tầng vật lý, hypervisor, hệ điều hành và runtime của môi trường thực thi. Khách hàng lo code và thư viện đóng gói kèm, quyền (execution role, resource policy), dữ liệu (phân loại, mã hoá, ai đọc được) |
| cut-bill | a, b, c, d | Tag rồi lọc Cost Explorer để biết tiền đi đâu; tắt staging ngoài giờ; retention log; Graviton rẻ hơn khoảng 20% cùng hiệu năng. Xoá budget alarm không giảm chi phí mà chỉ làm bạn biết muộn hơn |
