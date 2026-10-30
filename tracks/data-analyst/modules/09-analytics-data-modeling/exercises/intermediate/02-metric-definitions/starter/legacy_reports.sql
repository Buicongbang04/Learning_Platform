-- Hai truy vấn dashboard cũ (không sửa, không chấm): đọc để trả lời trắc nghiệm.
-- Bảng raw_sales_lines: sheet Year 2010-2011 nguyên trạng (tên cột như xlsx).

-- Dashboard Finance cũ: "Doanh thu tháng"
SELECT strftime("InvoiceDate", '%Y-%m') AS month,
       sum("Quantity" * "Price")        AS revenue
FROM raw_sales_lines
GROUP BY 1
ORDER BY 1;

-- Dashboard Marketing cũ: "Doanh thu và AOV theo tháng"
SELECT strftime("InvoiceDate", '%Y-%m') AS month,
       sum("Quantity" * "Price")        AS revenue,
       avg("Quantity" * "Price")        AS aov
FROM raw_sales_lines
WHERE "Customer ID" IS NOT NULL
  AND NOT starts_with(CAST("Invoice" AS VARCHAR), 'C')
  AND "Quantity" > 0 AND "Price" > 0
GROUP BY 1
ORDER BY 1;
