-- Funnel có thứ tự theo visitor: view -> addtocart (từ lần view đầu) -> transaction (từ lần addtocart đó).
-- Ba dòng: (1, 'view'), (2, 'addtocart'), (3, 'transaction').
-- Cột: step, event, visitors, conv_from_prev, conv_from_first
-- TODO: viết một câu SELECT (được dùng WITH) thay cho dòng dưới
SELECT NULL AS step, NULL AS event, NULL AS visitors, NULL AS conv_from_prev, NULL AS conv_from_first
