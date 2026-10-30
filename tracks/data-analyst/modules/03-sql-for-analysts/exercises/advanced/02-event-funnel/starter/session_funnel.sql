-- Funnel có thứ tự theo phiên (session): phiên mới khi cách sự kiện trước của cùng visitor hơn 30 phút.
-- Ba dòng: (1, 'view'), (2, 'addtocart'), (3, 'transaction'), mọi bước trong cùng một phiên.
-- Cột: step, event, sessions, conv_from_prev, conv_from_first
-- TODO: viết một câu SELECT (được dùng WITH) thay cho dòng dưới
SELECT NULL AS step, NULL AS event, NULL AS sessions, NULL AS conv_from_prev, NULL AS conv_from_first
