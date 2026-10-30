-- KPI theo tháng trên bảng online_retail (dòng hợp lệ: không bắt đầu bằng 'C', quantity > 0, price > 0).
-- Mỗi tháng từ tháng đầu tới tháng cuối có dữ liệu một dòng, kể cả tháng không có dòng hợp lệ.
-- Cột: month (DATE, ngày 1), revenue, orders, active_days, mom_pct, yoy_pct, ytd_revenue, is_complete
-- Sắp theo month.
-- TODO: viết một câu SELECT (được dùng WITH) thay cho dòng dưới
SELECT NULL AS month, NULL AS revenue, NULL AS orders, NULL AS active_days,
       NULL AS mom_pct, NULL AS yoy_pct, NULL AS ytd_revenue, NULL AS is_complete
