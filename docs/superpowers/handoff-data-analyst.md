# Bàn giao: track Data Analyst (tiếp tục trên PC RTX 3060 12GB)

Ngày bàn giao: 2026-10-31. Tài liệu này dành cho phiên Claude Code tiếp theo, chạy trên PC của người học. Hãy đọc hết trước khi làm bất cứ việc gì.

Track Data Analyst **đã xong và đã merge vào `main`** (PR #4 cho giai đoạn 1–2, PR #5 cho giai đoạn 3). Trên PC không còn việc bắt buộc nào. Tài liệu này giúp bạn:

1. dựng lại môi trường để chạy và học track trên PC;
2. biết những gì còn để ngỏ, nếu người học muốn làm tiếp;
3. tránh xung đột khi merge track AI Engineer (nhánh `ai-engineer`) vào `main`.

Track AI Engineer có tài liệu bàn giao riêng, `docs/superpowers/handoff-ai-engineer.md`, trên nhánh `ai-engineer`.

## 1. Người học và mục tiêu (đã chốt với người học)

- Người học viết tiếng Việt và muốn nội dung bằng tiếng Việt, giữ thuật ngữ tiếng Anh. Trước track này, người học đã xong track Data Engineer và AI & Data Scientist.
- Mục tiêu của track: học và thực hành cho công việc DA, vững kiến thức và kỹ năng trước khi đi phỏng vấn, nhắm tới chuẩn **DA senior** ("thừa hơn thiếu").
- Phần trùng với track cũ chỉ nhắc lại ngắn, có link về module gốc. Phần lớn track là bài tập, và **bài tập phải khác** bài của track DE/DS.
- Hai điểm yếu người học tự nêu, nên được lồng vào suốt track:
  - biết công dụng, điểm mạnh và yếu của từng công cụ: Excel, SQL, Python, R, Metabase, Superset, Power BI, Tableau, Looker, Streamlit;
  - kỹ năng phân tích và đọc biểu đồ.
- R chỉ giới thiệu. Power BI, Tableau và Looker chỉ dạy khái niệm và so sánh. Phần thực hành BI dùng Metabase, Superset và Streamlit.
- Cách làm việc:
  - subagent-driven: mỗi phần việc có một implementer và một reviewer độc lập, sửa đến khi review sạch;
  - người học muốn nhiều subagent chạy song song, mỗi agent một worktree riêng;
  - track AI Engineer đã chốt **tối đa 2 module song song**, sau khi laptop quá tải (load average 20–40).
- Commit message viết tiếng Việt và **không bao giờ** có dòng `Co-Authored-By`.
- Dùng dữ liệu thật. Dữ liệu sinh ra chỉ được dùng làm fixture cho test.
- Hỏi người học trước khi merge vào `main` hoặc push.

## 2. Tài liệu gốc

1. Spec: `docs/superpowers/specs/2026-10-29-data-analyst-track-design.md`.
2. Plan giai đoạn 1–2: `docs/superpowers/plans/2026-10-29-data-analyst-phase1-2.md`. Gồm hạ tầng quiz-only, 3 bộ dữ liệu và module mẫu 08.
3. Plan giai đoạn 3: `docs/superpowers/plans/2026-10-30-data-analyst-phase3.md`. Gồm app Excel/quiz, `Exercise.workbook()`, dịch vụ BI, 14 module và capstone. Mục **"Định nghĩa dùng chung"** là định nghĩa bắt buộc cho mọi module: cách làm sạch Online Retail II, khách hàng, cohort và retention.
4. `CONTENT_SPEC.md`: mục "Bài Excel", "Quiz trên bài không phải notebook", "Bài chỉ có trắc nghiệm" và quy tắc quiz (độ dài đáp án, giữ nguyên id).
5. `tracks/data-analyst/README.md`: lộ trình, bảng module, bảng so sánh công cụ.
6. `tracks/data-analyst/capstone/README.md`: dunnhumby, 5 tình huống trong đề Drive của người học, định nghĩa và số tham chiếu.
7. `setup/SETUP.md`, mục 5 và 11: dịch vụ BI, tài khoản, các biến môi trường.
8. Tham khảo thêm `data/README.md` cho nguồn, giấy phép và số dòng của từng bộ dữ liệu.

## 3. Trạng thái (lúc bàn giao)

| Phần | Trạng thái | Ghi chú |
| --- | --- | --- |
| 15 module, 108 bài | Xong, đã review, nằm trên `main` | Module 02, 08, 12 có 8 bài; các module còn lại 7 bài |
| Capstone dunnhumby, 7 milestone | Xong, đã review | `track.json` đã có khoá `capstone` |
| App: bài quiz-only, quiz trên bài code/Excel, tệp `.xlsx` hiện là tệp nhị phân kèm nút mở bằng LibreOffice | Xong | `app/src/code/exerciseKind.ts`, `QuizOnlyPanel.tsx`, `app/server/workspace.ts` |
| `testkit.Exercise.workbook()` | Xong | Tính lại công thức bằng LibreOffice headless, có cache. Thiếu `soffice` thì test tự SKIP |
| Dịch vụ BI | Xong | Superset 6.1.0 và Metabase, cả hai bind `127.0.0.1`. Script ở `setup/bi/` |

Kết quả kiểm trên laptop, lúc merge PR #5:

| Lệnh | Kết quả |
| --- | --- |
| `SOLUTION=1 uv run pytest tracks/data-analyst -q` | 538 passed, 210 skipped (skip là bài Advanced và bài BI khi dịch vụ tắt), 0 failed |
| Chạy test trên starter | 747 failed, 0 ERROR. Test duy nhất PASS là `test_berkeley_constant` ở module 08, vì nó chỉ kiểm hằng số có sẵn |
| `uv run pytest tests -q` | 321 passed |
| `cd app && pnpm test` | 29/29; `pnpm typecheck` và `pnpm build` đều OK |
| `SOLUTION=1 uv run pytest tracks/data-engineer tracks/data-science -q` | 1663 passed, 515 skipped, giống `origin/main` trước khi merge |

## 4. Merge `ai-engineer` vào `main`: xung đột đã biết

Lúc bàn giao, `git merge-tree origin/main origin/ai-engineer` báo **xung đột ở 4 tệp**. Hai nhánh cùng thêm vào các danh sách, nên cần **giữ cả hai phía**:

- `data/download_dataset.py`: registry `DATASETS`.
  - DA thêm: `bike-sharing-uci`, `online-retail-ii`, `dunnhumby-complete-journey`, `grocery-sales-synthetic`, `marketing-ab`, `ecommerce-events`, `owid-co2`, và hàm `_reject_html` chặn trang HTML từ Google Drive.
  - AE thêm các bộ riêng của AE.
- `tests/test_download_dataset.py`: danh sách khoá mong đợi. Gộp cả hai danh sách.
- `pyproject.toml`: dependency.
  - DA thêm `plotly`, `openpyxl`, `beautifulsoup4`, `lxml`, `mlxtend`.
  - AE thêm nhóm của AE và `constraint-dependencies`.
- `uv.lock`: đừng sửa tay. Sau khi gộp `pyproject.toml`, chạy `uv lock` rồi `uv sync`.

Sau khi merge:

- `uv run pytest tests -q`;
- kiểm torch vẫn là bản `+cpu`: `uv run python -c "import torch; print(torch.__version__)"`;
- `SOLUTION=1 uv run pytest tracks -q`;
- `cd app && pnpm test && pnpm build`.

Những tệp còn lại không cần xử lý tay:

- Nhánh `ai-engineer` không sửa `testkit.py`, `CONTENT_SPEC.md`, `setup/docker-compose.yml` hay `app/`.
- `data/README.md` và `setup/SETUP.md` tự merge được.
- AE thêm mới `llmkit.py`, `setup/gpu/` và `tests/test_llmkit.py`.

Nội dung mục này đã thống nhất với phiên AI Engineer; `handoff-ai-engineer.md` ghi cùng nội dung.

## 5. Bài học từ review (áp dụng nếu viết thêm nội dung DA)

Đây là những lỗi reviewer đã bắt được, và nhiều lỗi lặp lại ở nhiều module:

- **Bike Sharing thiếu giờ.**
  - `hour.csv` có ngày 2012-10-29 chỉ có giờ 0 (22 lượt), ngày 2012-10-30 chỉ có giờ 13–23, ngày 2011-08-27 có 18 giờ, và 76 ngày thiếu ít nhất 1 giờ.
  - Hai module (01 và 13) từng hiểu nhầm "bão Sandy, 22 lượt" là cầu thật.
  - Luôn kiểm độ phủ giờ trước khi diễn giải các điểm cực trị.
  - Nhãn mùa giữ theo UCI Readme (1 = spring), dù dữ liệu cho thấy mùa 1 thực ra là 21/12–20/3. Module 08 dùng chỗ lệch này làm bài học.
- **Online Retail II.**
  - Tháng 12/2011 chỉ có dữ liệu tới ngày 9 (9 ngày lịch, 8 ngày có giao dịch).
  - Hoá đơn 581483 trị giá 168 470 GBP bị huỷ 12 phút sau, và nó làm phồng mức "+45.6% YoY". Module 08 lý thuyết đã có cảnh báo; bài Advanced 01 đào sâu chuyện này.
  - Hai sheet chồng nhau đoạn 2010-12-01..09.
  - File xlsx đọc chậm (20–90 giây). Bản đã làm sạch được cache thành parquet trong `tempfile.gettempdir()/da-cache`, khoá theo mtime và size của xlsx. Không bao giờ ghi vào `data/raw`.
- **Không dùng số bịa làm dữ liệu học.** Chi phí, biên lợi nhuận, CAC và voucher không có trong dữ liệu, nên phải ghi rõ "ví dụ giả định". Ngoại lệ duy nhất là bộ synthetic Grocery Sales, chỉ dùng cho bài "nghi ngờ dữ liệu" (module 06) và để thiết kế schema (module 09).
- **Kiểm phép tính quyết định.** Ví dụ ở module 11: ngưỡng hoà vốn tính trên doanh thu theo giá niêm yết là +33%, trong khi tính trên doanh thu sau voucher 10% (biên 40%) chỉ là +20%. Lẫn hai metric này sẽ đảo kết luận về power của thí nghiệm.
- **Thông tin pháp lý phải có ngày.** Tính tới 10/2026, dữ liệu cá nhân ở Việt Nam chịu Luật 91/2025/QH15 và Nghị định 356/2025/NĐ-CP (thay Nghị định 13/2023), cùng hiệu lực từ 01/01/2026. Ghi rõ "không phải tư vấn pháp lý". Tên sản phẩm AI cũng cần ghi mốc thời gian.
- **Quiz.**
  - Đáp án phải rải đều các vị trí a/b/c/d. Module 02 từng dồn vào "b".
  - Tuân quy tắc độ dài đáp án.
  - Câu `data` phải khớp với output của notebook mà người học thực sự chạy. Module 13 từng có câu quiz dùng số khi chưa kiểm độ phủ, trong khi cell explore đã kiểm.
- **Test.**
  - Starter chỉ được FAIL hoặc SKIP, không được ERROR, nên không gọi hàm của người học trong fixture.
  - Không ghim thứ hạng của hai số chênh nhau ở mức nhiễu.
  - Test gọi API Metabase/Superset phải tạo object có tiền tố riêng và dọn trong teardown.
  - Khi Superset chưa sẵn sàng thì SKIP, không để ERROR.
- **App.** Tệp nhị phân không được cắt theo `MAX_FILE_BYTES`. Lỗi này từng làm 2 workbook trên 256 KB biến mất khỏi app.

## 6. Các quyết định đã tự đưa ra (người học đọc lại để sửa nếu không đồng ý)

| Quyết định | Lý do | Rủi ro nếu sai |
| --- | --- | --- |
| Capstone dùng dunnhumby "The Complete Journey" (Kaggle `frtgnn`, ODbL/DbCL), không dùng bộ Grocery Sales trong Drive | Bộ Drive là dữ liệu sinh: `TotalPrice` = 0 ở mọi dòng, mỗi hoá đơn chỉ 1 dòng hàng, phân phối phẳng | Người học có thể muốn dùng đúng bộ Drive |
| Ánh xạ 5 tình huống của đề Drive: "nhân viên" thành `STORE_ID`, "địa lý" thành nhân khẩu học (801/2 500 hộ có dữ liệu) | dunnhumby không có nhân viên và không có địa lý | Chỉ cần sửa chữ trong capstone |
| Bộ funnel là Retail Rocket (Kaggle ghi CC0, bản gốc CC BY-NC-SA): chỉ dùng để học, không commit mẫu | Bộ mkechinov có giấy phép "© tác giả"; Instacart có giấy phép đáng ngờ, nên market basket dùng Online Retail II | Đổi bộ dữ liệu ở module 12 |
| `owid-co2` ghim theo commit SHA `382ee6c` | Nhánh `master` thay đổi theo thời gian, làm số trong quiz trôi | — |
| Module chạy song song trên các worktree riêng, rồi cherry-pick về nhánh tích hợp | Người học muốn nhiều subagent | Chỉ tốn thêm việc gộp commit |
| Code đọc Online Retail bị lặp ở nhiều bài, không đưa vào testkit | Notebook phải chạy độc lập; plan cấm sửa hạ tầng trong task module | Code có thể lệch nhau về sau. Reviewer đã so các bản và lúc merge chưa thấy lệch |
| Metabase và Superset chỉ bind `127.0.0.1` | Superset dùng admin/admin và `SECRET_KEY` mặc định | Không mở được từ máy khác trong mạng LAN; sửa trong compose nếu cần |
| Module 11 Advanced 02: "chiến dịch" là kịch bản giả định đặt trên dữ liệu thật | Online Retail không ghi lại chiến dịch nào | Có ghi rõ trong đề |
| Đã rà 72 bộ quiz bằng Gemini (OmniRoute, `auto/gemini-3.8-flash`), coi là ý kiến thứ hai | Rẻ và nhanh; tìm ra 1 lỗi làm tròn (6 922 so với 6 921) | Gemini có thể bỏ sót; review chính vẫn do Claude làm |

## 7. Việc còn để ngỏ (không chặn việc học, làm nếu người học muốn)

- Gom các bản sao code đọc Online Retail (module 03, 04, 06, 07, 09, 11, 12, 13, 14) vào một helper chung, ví dụ trong `testkit.py`. Cache key nên có thêm phiên bản loader.
- Module 14 Basic 03 dùng multiprocessing với context "fork", nên chỉ chạy trên Linux. Có thể thêm SKIP khi nền tảng không hỗ trợ fork.
- Module 14 Intermediate 02: test k-means ghim đúng thứ tự tên segment. Có thể so sánh tên sau khi sắp xếp.
- Module 09: tắt telemetry của dbt (`DBT_SEND_ANONYMOUS_USAGE_STATS=False`). Đoạn dbt trong README nên dọn thư mục trong `finally`.
- Module 10: teardown chưa kiểm status của lệnh DELETE.
- `pivot_tables()` của `Exercise.workbook` đọc thuộc tính riêng tư `_pivots` của openpyxl.
- Bộ `grocery-sales-synthetic` tải từ Google Drive chưa có checksum. Đã có chặn trang HTML.
- Module 05: `pipeline.py --last 0` chưa bị từ chối.
- Câu chữ nhỏ ở SOLUTION module 01, Basic 03 ("vài ngày bão sai 200–300%") và Intermediate 02 ("30/10, 1 096 lượt" thực ra chỉ có 11 giờ dữ liệu).

## 8. Runbook trên PC

### 8.1 Chuẩn bị máy

```bash
git clone <remote> DataScience && cd DataScience
git checkout main && git pull
uv sync
cd app && pnpm install --frozen-lockfile && cd ..
sudo apt install libreoffice-calc     # bài Excel module 02 cần `soffice`
```

- Docker: cần cho module 10 (BI) và một số bài của track DE.
- Nếu PC không có dự án nào khác chiếm cổng 5432/6379/9000/9001, bỏ phần remap trong `setup/.env`. Xem `setup/.env.example`.

### 8.2 `setup/.env` (không commit)

Chép từ laptop hoặc tạo mới với các biến sau:

- `KAGGLE_API_TOKEN=KGAT_...`: cần để tải dunnhumby, marketing-ab, ecommerce-events, store-sales, telco-churn và Olist.
- Các biến cổng, nếu cần.
- Các biến OmniRoute, nếu muốn dùng Gemini làm reviewer phụ: `OMNIROUTE_BASE_URL`, `OMNIROUTE_API_KEY`, `OMNIROUTE_MODEL=auto/gemini-3.8-flash`.
- `METABASE_ADMIN_EMAIL` / `METABASE_ADMIN_PASSWORD`: chỉ cần khi Metabase đã được setup bằng tài khoản khác. Mặc định là `admin@example.com` / `DeLearning-Admin1`.

### 8.3 Dữ liệu (`data/raw` không nằm trong git, khoảng 5,4 GB trên laptop)

```bash
uv run python data/download_dataset.py --list
for d in bike-sharing-uci online-retail-ii dunnhumby-complete-journey grocery-sales-synthetic \
         marketing-ab ecommerce-events owid-co2 store-sales telco-churn open-meteo; do
  uv run python data/download_dataset.py "$d"
done
uv run python data/download_olist.py      # module 08 Intermediate 03 dùng Olist
```

- `grocery-sales-synthetic` tải từ thư mục Google Drive mà người học đưa, khoảng 517 MB. Giấy phép không rõ, nên chỉ dùng cục bộ.
- Cách nhanh hơn là chép nguyên thư mục `data/raw` từ laptop sang.
- Lần đầu chạy, các bài Online Retail đọc xlsx chậm. Từ lần sau sẽ đọc từ cache parquet trong thư mục temp.

### 8.4 Dịch vụ BI (module 10, capstone milestone m04)

```bash
docker compose -f setup/docker-compose.yml --profile bi up -d postgres metabase superset
uv run python setup/bi/init_bi.py     # tạo admin Metabase, kết nối DB cho Metabase và Superset (chạy lại nhiều lần vẫn an toàn)
uv run python setup/bi/load_da.py     # nạp schema `da`: online_retail_ii, bike_hour (đọc xlsx ~1 phút, RAM >1 GB)
uv run pytest tests/test_bi_services.py -q
```

- Metabase chạy ở `http://127.0.0.1:3000`, Superset ở `http://127.0.0.1:8088` (admin/admin).
- Tắt mà vẫn giữ dữ liệu: `docker compose -f setup/docker-compose.yml stop superset metabase`.
- Không chạy `down -v`.

### 8.5 Kiểm sau khi dựng máy

Chạy đủ các lệnh ở mục 3. Kết quả phải giống: 0 failed khi có `SOLUTION=1`, và 0 ERROR khi chạy trên starter. Riêng bài BI sẽ SKIP nếu dịch vụ đang tắt.

### 8.6 Nếu viết thêm nội dung DA

- Theo quy trình Task 4–17 trong plan giai đoạn 3.
- Mỗi module làm trong một worktree riêng:
  ```bash
  git worktree add -b da-<tên> ../DataScience-da-<tên> main
  ln -s "$PWD/data/raw" ../DataScience-da-<tên>/data/raw
  ```
  Sau đó chép `setup/.env` sang worktree và chạy `uv sync`.
- Dispatch một implementer kèm plan, dòng của module trong plan, và các quy tắc ở mục 5. Sau đó dispatch một reviewer độc lập.
- Gộp vào `main` qua PR, và chỉ làm khi người học đồng ý.
