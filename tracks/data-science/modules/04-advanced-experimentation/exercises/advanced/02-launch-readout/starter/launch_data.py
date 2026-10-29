"""Log giả lập của thí nghiệm 4 tuần trên một app đọc truyện: giao diện trang chủ mới.

Không sửa tệp này. Dùng trong notebook:

    from launch_data import make_launch_log
    log = make_launch_log()

Mỗi dòng là một user-ngày có mở app: user_id, treat (0/1), segment ("existing" / "new"),
platform ("android" / "ios"), first_day (ngày đầu tiên user thấy thí nghiệm), day (0..27), minutes
(số phút đọc trong ngày). User được random 50/50 theo user_id.

Không có dữ liệu thật công khai nào ghi lại novelty effect theo ngày ở mức user, nên bộ này được
sinh ra với các tham số ẩn. Đừng đọc code sinh dữ liệu trước khi phân tích xong: hãy coi nó như dữ
liệu thật, rồi đối chiếu kết luận của bạn với tham số ở cuối SOLUTION.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_launch_log(seed: int = 0, n_users: int = 20000, n_days: int = 28) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    user = np.arange(n_users)
    treat = (rng.random(n_users) < 0.5).astype(int)
    existing = rng.random(n_users) < 0.7
    platform = np.where(rng.random(n_users) < 0.6, "android", "ios")
    first_day = np.where(existing, rng.integers(0, 7, n_users), rng.integers(0, 21, n_users))
    base = np.where(existing, rng.lognormal(np.log(20), 0.5, n_users), rng.lognormal(np.log(12), 0.6, n_users))
    p_active = np.where(existing, 0.6, 0.4)

    rows = []
    for d in range(n_days):
        on = (first_day <= d) & (rng.random(n_users) < p_active)
        idx = user[on]
        exposure = d - first_day[idx]
        weekend = 1.25 if d % 7 in (5, 6) else 1.0
        effect = np.where(existing[idx], 3.0 * np.exp(-exposure / 4) + 0.5, 1.0) * treat[idx]
        minutes = np.maximum(0, base[idx] * weekend + effect + rng.normal(0, 6, len(idx)))
        rows.append(pd.DataFrame({
            "user_id": idx, "treat": treat[idx], "segment": np.where(existing[idx], "existing", "new"),
            "platform": platform[idx], "first_day": first_day[idx], "day": d, "minutes": minutes.round(2),
        }))
    return pd.concat(rows, ignore_index=True)
