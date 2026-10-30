# Dunnhumby: The Complete Journey

Dự án capstone xuyên suốt lộ trình Data Analyst. Bạn đóng vai Data Analyst của một chuỗi siêu thị
(grocery/FMCG) ở Mỹ, trả lời ban điều hành ba nhóm câu hỏi: **doanh thu đang đến từ đâu, khách hàng nào
tạo ra nó, và các chương trình marketing (campaign, coupon) có hiệu quả không**. Bảy milestone đi từ nạp và
làm sạch dữ liệu, SQL, star schema, dashboard, phân khúc khách hàng, đánh giá campaign tới memo cho ban điều hành.

Dữ liệu là **dữ liệu thật** do dunnhumby công bố: các giao dịch của 2 500 hộ gia đình có thẻ khách hàng
trong khoảng hai năm. Vì là dữ liệu thật nên có chỗ "khó chịu" mà bạn phải tự phát hiện và nói rõ cách
xử lý (xem phần Cạm bẫy).

## Mục tiêu dự án

- Một **câu chuyện liền mạch** từ dữ liệu tới quyết định: mỗi con số trong memo cuối truy được về một
  notebook, câu SQL hoặc dashboard chạy lại được.
- Thể hiện kỹ năng nhà tuyển dụng hỏi ở vị trí Data Analyst senior: định nghĩa metric, SQL, data modeling,
  dashboard, RFM/cohort, đọc kết quả thí nghiệm có giới hạn và giao tiếp với stakeholder.
- Trung thực: "chưa đủ bằng chứng để kết luận campaign có hiệu quả" là kết luận tốt nếu dữ liệu nói vậy.

## Dữ liệu

```bash
uv run python data/download_dataset.py dunnhumby-complete-journey   # cần Kaggle token, ghi vào data/raw/dunnhumby-complete-journey/
```

Nguồn: [Kaggle `frtgnn/dunnhumby-the-complete-journey`](https://www.kaggle.com/datasets/frtgnn/dunnhumby-the-complete-journey),
giấy phép ODbL (database) / DbCL v1.0 (contents). Không commit dữ liệu thô. `causal_data.csv` rất lớn (~696 MB,
36,8 triệu dòng): đọc bằng DuckDB hoặc `usecols`/`chunksize`, không `read_csv` cả tệp bằng pandas.

### Schema 8 bảng

| Tệp | Số dòng | Một dòng là | Cột chính |
| --- | --- | --- | --- |
| `transaction_data.csv` | 2 595 732 | một mặt hàng trong một giỏ | `household_key`, `BASKET_ID`, `DAY`, `WEEK_NO`, `PRODUCT_ID`, `STORE_ID`, `QUANTITY`, `SALES_VALUE`, `RETAIL_DISC`, `COUPON_DISC`, `COUPON_MATCH_DISC`, `TRANS_TIME` |
| `product.csv` | 92 353 | một sản phẩm | `PRODUCT_ID`, `DEPARTMENT`, `COMMODITY_DESC`, `SUB_COMMODITY_DESC`, `BRAND`, `MANUFACTURER`, `CURR_SIZE_OF_PRODUCT` |
| `hh_demographic.csv` | 801 | một hộ có thông tin nhân khẩu | `household_key`, `AGE_DESC`, `INCOME_DESC`, `HOMEOWNER_DESC`, `HH_COMP_DESC`, `HOUSEHOLD_SIZE_DESC`, `KID_CATEGORY_DESC`, `MARITAL_STATUS_CODE` |
| `campaign_desc.csv` | 30 | một campaign | `CAMPAIGN`, `DESCRIPTION` (TypeA/B/C), `START_DAY`, `END_DAY` |
| `campaign_table.csv` | 7 208 | một hộ được gán vào một campaign | `household_key`, `CAMPAIGN`, `DESCRIPTION` |
| `coupon.csv` | 124 548 | một sản phẩm thuộc một coupon của một campaign | `COUPON_UPC`, `PRODUCT_ID`, `CAMPAIGN` |
| `coupon_redempt.csv` | 2 318 | một lần hộ dùng coupon | `household_key`, `DAY`, `COUPON_UPC`, `CAMPAIGN` |
| `causal_data.csv` | 36 786 524 | một sản phẩm tại một cửa hàng trong một tuần | `PRODUCT_ID`, `STORE_ID`, `WEEK_NO`, `display`, `mailer` |

```mermaid
erDiagram
    HH_DEMOGRAPHIC ||--o{ TRANSACTION : "household_key"
    PRODUCT ||--o{ TRANSACTION : "PRODUCT_ID"
    HH_DEMOGRAPHIC ||--o{ CAMPAIGN_TABLE : "household_key"
    CAMPAIGN_DESC ||--o{ CAMPAIGN_TABLE : "CAMPAIGN"
    CAMPAIGN_DESC ||--o{ COUPON : "CAMPAIGN"
    PRODUCT ||--o{ COUPON : "PRODUCT_ID"
    COUPON ||--o{ COUPON_REDEMPT : "COUPON_UPC, CAMPAIGN"
    PRODUCT ||--o{ CAUSAL_DATA : "PRODUCT_ID"
    TRANSACTION {
        int household_key
        bigint BASKET_ID
        int DAY
        int WEEK_NO
        int PRODUCT_ID
        int STORE_ID
        int QUANTITY
        float SALES_VALUE
        float RETAIL_DISC
        float COUPON_DISC
        float COUPON_MATCH_DISC
    }
    PRODUCT {
        int PRODUCT_ID
        string DEPARTMENT
        string COMMODITY_DESC
        string BRAND
    }
    HH_DEMOGRAPHIC {
        int household_key
        string AGE_DESC
        string INCOME_DESC
    }
    CAMPAIGN_DESC {
        int CAMPAIGN
        string DESCRIPTION
        int START_DAY
        int END_DAY
    }
    CAMPAIGN_TABLE {
        int household_key
        int CAMPAIGN
    }
    COUPON {
        bigint COUPON_UPC
        int PRODUCT_ID
        int CAMPAIGN
    }
    COUPON_REDEMPT {
        int household_key
        int DAY
        bigint COUPON_UPC
        int CAMPAIGN
    }
    CAUSAL_DATA {
        int PRODUCT_ID
        int STORE_ID
        int WEEK_NO
        string display
        string mailer
    }
```

`hh_demographic` chỉ có **801 trong 2 500 hộ** (32%): phân tích theo nhân khẩu học chỉ áp dụng cho nhóm này
và nhóm đó có thể không đại diện. `DAY` đếm từ 1 là ngày đầu của dữ liệu, không phải ngày lịch; bộ dữ liệu
**không có ngày lịch thật và không có địa lý** (chỉ có `STORE_ID`).

## Định nghĩa dùng chung

Mọi milestone dùng **cùng** các định nghĩa dưới đây. Đổi định nghĩa nào thì ghi rõ trong báo cáo và lý do.

| Khái niệm | Định nghĩa |
| --- | --- |
| Doanh thu ròng | `SUM(SALES_VALUE)`: số tiền cửa hàng thực nhận sau khi trừ giảm giá thẻ (`RETAIL_DISC`) và phần cửa hàng khớp coupon (`COUPON_MATCH_DISC`) |
| Doanh thu trước giảm giá (giá niêm yết) | `SALES_VALUE - RETAIL_DISC - COUPON_MATCH_DISC` (hai cột giảm giá là số âm) |
| Tỷ lệ giảm giá | `-(RETAIL_DISC + COUPON_MATCH_DISC + COUPON_DISC) / doanh thu trước giảm giá`; `COUPON_DISC` là coupon của nhà sản xuất, được thêm vào để đo tổng ưu đãi khách nhận |
| Basket (giỏ hàng) | một giá trị `BASKET_ID`; giá trị basket = tổng `SALES_VALUE` của các dòng cùng `BASKET_ID` |
| AOV | doanh thu ròng chia số basket |
| Kích thước basket | số dòng (mặt hàng) hoặc tổng `QUANTITY` trong một basket; nói rõ dùng cái nào |
| Hộ (khách hàng) | `household_key`, không có khái niệm cá nhân |
| Repeat vs one-time | hộ có từ 2 basket trở lên (khác `BASKET_ID`) trong dữ liệu là repeat, đúng 1 basket là one-time |
| Dòng hợp lệ để tính doanh thu | `SALES_VALUE > 0` và `QUANTITY > 0` (xem Cạm bẫy: dòng trả hàng/điều chỉnh) |
| Thời gian | `DAY` (1..711) và `WEEK_NO` (1..102); báo cáo theo tuần hoặc theo "tháng" = 4 tuần liên tiếp, ghi rõ quy ước |

### Về định nghĩa doanh thu

Chưa đối chiếu được tài liệu hướng dẫn chính thức của dunnhumby (không truy cập được khi biên soạn), nên định nghĩa trên dựa trên **kiểm tra trực tiếp trên dữ liệu**, chưa phải tài liệu chính thức: với các dòng
có `COUPON_MATCH_DISC < 0`, giá `SALES_VALUE - RETAIL_DISC - COUPON_MATCH_DISC` chia số lượng cho ra mức giá
niêm yết "tròn" hợp lý (2,19; 2,99; 2,29), còn `SALES_VALUE` đơn lẻ thì là số lẻ (1,10; 2,05). Suy ra
`SALES_VALUE` đã **net** của `RETAIL_DISC` và `COUPON_MATCH_DISC`. `COUPON_DISC` là phần nhà sản xuất chi trả cho coupon, nên **không** trừ vào doanh thu ròng của cửa hàng.
Nếu tìm được tài liệu chính thức khác với kết luận này, hãy sửa bảng định nghĩa và ghi lại. Đây cũng là
ví dụ của một kỹ năng DA senior: kiểm định nghĩa cột bằng dữ liệu trước khi tin tên cột.

## Con số tham chiếu

Tính bằng DuckDB trực tiếp trên tệp CSV đã tải (không lọc), để bạn đối chiếu kết quả của mình:

| Đại lượng | Giá trị |
| --- | --- |
| Số dòng `transaction_data` | 2 595 732 |
| Số hộ có giao dịch | 2 500 |
| Số basket (`BASKET_ID` khác nhau) | 276 484 |
| Số sản phẩm có bán / số sản phẩm trong `product` | 92 339 / 92 353 |
| Số cửa hàng (`STORE_ID`) | 582 |
| Khoảng `DAY` | 1 .. 711 (711 ngày khác nhau, không bị hổng ngày) |
| Khoảng `WEEK_NO` | 1 .. 102 |
| Tổng `SALES_VALUE` | 8 057 463,08 |
| Tổng `RETAIL_DISC` / `COUPON_MATCH_DISC` / `COUPON_DISC` | -1 398 334,84 / -7 575,81 / -42 611,54 |
| Doanh thu trước giảm giá (`SALES_VALUE - RETAIL_DISC - COUPON_MATCH_DISC`) | 9 463 373,73 |
| Giá trị basket trung bình / trung vị | 29,14 / 17,07 |
| Số dòng mỗi basket, trung vị | 5 |
| Dòng có `SALES_VALUE <= 0` hoặc `QUANTITY <= 0` | 18 917 (trong đó 18 850 dòng `SALES_VALUE = 0`) |
| Số hộ trong `hh_demographic` | 801 |
| Số hộ trong `campaign_table` / số campaign | 1 584 / 30 |
| Số hộ dùng coupon (`coupon_redempt`) | 434 |
| Số ngành hàng (`DEPARTMENT`) | 44 |
| `causal_data`: số sản phẩm / số tuần | 68 377 / 93 |

## Cạm bẫy của dữ liệu thật

- **Dòng có `SALES_VALUE = 0`** (18 850 dòng): hàng tặng, khuyến mãi tặng kèm hoặc điều chỉnh. Giữ hay bỏ
  khi đếm số mặt hàng, đếm basket? Nói rõ lựa chọn. Tổng `SALES_VALUE` của dòng `> 0` trùng tổng toàn bộ
  tới sai số làm tròn, nghĩa là **không có dòng âm đáng kể**; vẫn cần tự kiểm lại sau khi lọc.
- **Chỉ 32% hộ có nhân khẩu học**, và `campaign_table` chỉ phủ 1 584/2 500 hộ.
- **`DAY` không phải ngày lịch**: không có tháng, mùa vụ thật; nếu cần "tháng" phải tự quy ước (4 tuần).
- **Dữ liệu cắt ở hai đầu**: tuần đầu và tuần cuối có thể thiếu ngày; đừng kết luận tăng/giảm từ chúng.
- **Hộ có thẻ khách hàng không phải toàn bộ khách của cửa hàng**: kết quả nói về nhóm hộ này.
- **Coupon redemption chỉ có 2 318 dòng** trên 434 hộ: mẫu nhỏ, đọc kết quả campaign phải cẩn thận.

## Câu hỏi xuyên suốt và 5 tình huống

Capstone phủ 5 tình huống phân tích của đề thực hành "Phân tích dữ liệu bán hàng siêu thị" (Grocery
Sales Database, thư mục Drive "Bài 18: Sales of FMCG Stores"), chuyển sang dữ liệu thật. Bộ gốc là dữ liệu
sinh ngẫu nhiên nên chỉ dùng cho bài "nghi ngờ dữ liệu" ở module 06; dunnhumby thay vào làm dữ liệu phân
tích. Vì dunnhumby khác schema, ba tình huống phải đổi cách ánh xạ (ghi rõ bên dưới).

| # | Tình huống (đề gốc) | Ánh xạ sang dunnhumby | Bảng dùng |
| --- | --- | --- | --- |
| 1 | Hiệu suất doanh thu theo thời gian: 1.1 doanh thu thực tế theo tháng; 1.2 tỷ trọng đóng góp của từng danh mục theo từng tháng | Doanh thu ròng theo tuần và theo "tháng" (4 tuần, ghi rõ quy ước); tỷ trọng theo `DEPARTMENT` / `COMMODITY_DESC` theo tháng. Chú ý hai đầu thời gian bị cắt | `transaction_data`, `product` |
| 2 | Định biên và phân loại sản phẩm: 2.1 top-5 / bottom-5 theo doanh thu; 2.2 tương quan Quantity vs doanh thu (volume cao, giá trị thấp); 2.3 ảnh hưởng của thuộc tính phân loại `Class` | 2.1 xếp hạng sản phẩm (bottom-5 chỉ xét sản phẩm có bán); 2.2 `QUANTITY` vs `SALES_VALUE`, tìm sản phẩm bán nhiều nhưng doanh thu mỗi đơn vị thấp; 2.3 dunnhumby **không có `Class`**, dùng thuộc tính tương đương của `product`: `BRAND` (National/Private) và `DEPARTMENT` | `transaction_data`, `product` |
| 3 | Hành vi và chân dung khách hàng: 3.1 phân khúc; 3.2 repeat vs one-time; 3.3 AOV và basket size | RFM trên `household_key`; repeat vs one-time và AOV, basket size theo định nghĩa chung ở trên | `transaction_data` |
| 4 | Năng lực thúc đẩy doanh số của nhân viên (`SalesPersonID`): 4.1 doanh số và số hoá đơn; 4.2 top / underperformer; 4.3 xu hướng theo thời gian, độ ổn định | **Thay bằng hiệu suất theo `STORE_ID`**: dunnhumby không có bảng nhân viên và không có cột người bán, `STORE_ID` là thực thể bán hàng duy nhất. 4.1 tổng doanh số và số basket mỗi cửa hàng; 4.2 nhóm vượt trội và dưới kỳ vọng (so với trung vị, nhớ chuẩn hoá theo quy mô, vì cửa hàng lớn hơn không có nghĩa là hiệu quả hơn); 4.3 độ ổn định doanh số theo tuần (hệ số biến thiên) | `transaction_data` |
| 5 | Doanh thu theo địa giới (thành phố, quốc gia): 5.1 tổng hợp phân cấp; 5.2 chênh lệch sản lượng giữa vùng; 5.3 chỉ số cho ban giám đốc | **Thay địa lý bằng nhân khẩu học**: dunnhumby không có địa lý. Tổng hợp doanh thu, sản lượng, AOV theo `AGE_DESC`, `INCOME_DESC`, `HOUSEHOLD_SIZE_DESC`, `KID_CATEGORY_DESC`. **Chỉ 801/2 500 hộ (32%) có dữ liệu nhân khẩu học**, nên mọi kết luận nói về nhóm này và phải nêu rõ giới hạn | `transaction_data`, `hh_demographic` |

Hai phần thêm so với đề gốc: **hiệu quả campaign/coupon** (`campaign_*`, `coupon*`, `causal_data`) và
**market basket**.

## Bức tranh tổng thể

```mermaid
flowchart LR
    RAW[(data/raw<br/>dunnhumby CSV)] --> CLEAN[M1 Nạp & làm sạch<br/>data dictionary]
    CLEAN --> SQL[M2 Câu hỏi business<br/>bằng SQL]
    CLEAN --> STAR[M3 Star schema<br/>& metric dùng chung]
    SQL --> STAR
    STAR --> DASH[M4 Dashboard<br/>Metabase/Superset + Streamlit]
    STAR --> SEG[M5 RFM, cohort,<br/>market basket]
    SEG --> CAMP[M6 Campaign / coupon<br/>như thí nghiệm có giới hạn]
    DASH --> MEMO[M7 Memo & thuyết trình<br/>cho ban điều hành]
    SEG --> MEMO
    CAMP --> MEMO
```

## Milestone

Mỗi milestone được gắn với module mà nó cần (`after`): app mở milestone khi bạn tới module đó, và
milestone chỉ đòi kiến thức của các module trước nó. Mỗi milestone dùng lại sản phẩm của milestone trước.

```mermaid
flowchart TB
    M06m[Module 06<br/>Làm sạch dữ liệu] -.-> C1[M01 Nạp, làm sạch,<br/>data dictionary]
    M07m[Module 07<br/>Thống kê mô tả & EDA] -.-> C2[M02 Tình huống 1–4<br/>bằng SQL]
    M09m[Module 09<br/>Data modeling] -.-> C3[M03 Star schema<br/>& METRICS.md]
    M10m[Module 10<br/>BI & Dashboard] -.-> C4[M04 Metabase/Superset<br/>+ Streamlit]
    M12m[Module 12<br/>Product & customer] -.-> C5[M05 RFM, cohort,<br/>basket, nhân khẩu học]
    M13m[Module 13<br/>Business & financial] -.-> C6[M06 Campaign/coupon]
    M15m[Module 15<br/>Stakeholder & storytelling] -.-> C7[M07 Memo & 5 slide]
    C1 --> C2 --> C3
    C3 --> C4
    C3 --> C5
    C5 --> C6
    C4 --> C7
    C5 --> C7
    C6 --> C7
```

| # | Milestone | Sau module | Dùng lại | Tạo ra |
| --- | --- | --- | --- | --- |
| M01 | [Nạp dữ liệu, làm sạch, data dictionary](milestones/m01-load-clean-dictionary.md) | `06-data-cleaning` | 8 CSV | `dunnhumby.duckdb`, `DATA_DICTIONARY.md`, `CLEANING_LOG.md` |
| M02 | [Trả lời tình huống 1–4 bằng SQL](milestones/m02-sql-business-questions.md) | `07-descriptive-eda` (SQL từ module 03) | M01 | `sql/m02/`, `SQL_ANSWERS.md` |
| M03 | [Star schema và định nghĩa metric dùng chung](milestones/m03-star-schema-metrics.md) | `09-analytics-data-modeling` | M01, M02 | star schema có test, `METRICS.md` |
| M04 | [Dashboard Metabase/Superset và Streamlit](milestones/m04-dashboards.md) | `10-bi-dashboards` | M03 | hai dashboard cùng số, `DASHBOARD.md` |
| M05 | [RFM, cohort retention, market basket, nhân khẩu học](milestones/m05-segmentation-cohort-basket.md) | `12-product-customer-analytics` | M03 | `SEGMENTS.md` (tình huống 3 và 5) |
| M06 | [Hiệu quả campaign/coupon](milestones/m06-campaign-coupon.md) | `13-business-financial-analytics` (DiD từ module 11) | M03, M05 | `CAMPAIGN.md`, đề xuất thí nghiệm |
| M07 | [Memo và thuyết trình cho ban điều hành](milestones/m07-exec-memo.md) | `15-stakeholder-storytelling-interview` | M01–M06 | `NUMBERS.md`, `MEMO.md`, 5 slide, README portfolio |

## Code của capstone

Code nằm ở [`project/`](project/). Khung gợi ý (bạn tự tạo dần, chi tiết trong `project/README.md`):

```
project/
├── src/dunnhumby_da/  # load, export_pg, segments, campaign: hàm dùng chung có test
├── sql/               # checks/ (M01), m02/, m05/, m06/
├── dbt/               # M03: star schema + test
├── notebooks/         # m01, m02, m05, m06
├── dashboards/        # M04: Streamlit + tệp xuất BI
├── reports/           # DATA_DICTIONARY, CLEANING_LOG, SQL_ANSWERS, MODEL, METRICS, DASHBOARD,
│                      # SEGMENTS, CAMPAIGN, NUMBERS, MEMO, QA_PREP, slides
├── artifacts/         # dunnhumby.duckdb, parquet: không commit
└── tests/             # uv run pytest tracks/data-analyst/capstone/project/tests -q
```

Capstone không có lời giải mẫu. Mỗi milestone có bảng số tham chiếu (tính bằng DuckDB trên dữ liệu thật)
để bạn đối chiếu; lệch thì tìm lý do và ghi lại, đừng chỉnh cho khớp.
