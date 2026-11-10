"""Sinh trace.csv: 2 000 request GIẢ LẬP trong 1 giờ của một chatbot CSKH (chỉ dùng làm fixture cho bài).

Không phải log thật. Hình dạng chọn để có các hiện tượng cần thấy: câu hỏi FAQ lặp theo phân phối Zipf,
câu hỏi cá nhân có cùng văn bản giữa nhiều người dùng ("đơn của tôi đâu"), một sự cố 10 phút của model chính
(t từ 1 500 tới 2 100 s) cộng 1.5% lỗi lẻ tẻ, độ trễ lognormal.

    uv run python tracks/ai-engineer/modules/21-ai-system-design/exercises/intermediate/02-gateway-simulator/tests/fixtures/make_trace.py
"""

import csv
from pathlib import Path

import numpy as np

N, HORIZON, USERS, FAQS = 2000, 3600.0, 400, 120
PERSONAL = ["p_order_status", "p_refund_status", "p_balance", "p_last_payment", "p_change_address",
            "p_cancel_order", "p_points", "p_invoice"]

rng = np.random.default_rng(2026)
t = np.sort(rng.uniform(0, HORIZON, N))
rows = []
zipf_w = 1 / np.arange(1, FAQS + 1) ** 1.1
zipf_w /= zipf_w.sum()
for i in range(N):
    personal = rng.random() < 0.45
    if personal:
        key = PERSONAL[rng.integers(len(PERSONAL))]
        in_tok = int(np.clip(rng.normal(2200, 400), 800, 4000))
        conf = rng.beta(3, 3)
    else:
        key = f"faq_{rng.choice(FAQS, p=zipf_w):03d}"
        in_tok = int(np.clip(rng.normal(1800, 300), 800, 4000))
        conf = rng.beta(6, 2)
    outage = 1500 <= t[i] < 2100
    rows.append({
        "id": i, "t": round(float(t[i]), 3), "user": f"u{rng.integers(USERS):03d}", "key": key,
        "personal": int(personal), "in_tok": in_tok, "out_tok": int(np.clip(rng.normal(220, 60), 40, 600)),
        "small_conf": round(float(conf), 3), "large_ok": int(not outage and rng.random() >= 0.015),
        "lat_small": round(float(rng.lognormal(np.log(0.5), 0.3)), 3),
        "lat_large": round(float(rng.lognormal(np.log(2.5), 0.35)), 3),
        "lat_fallback": round(float(rng.lognormal(np.log(1.8), 0.35)), 3),
    })
with open(Path(__file__).with_name("trace.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows")
