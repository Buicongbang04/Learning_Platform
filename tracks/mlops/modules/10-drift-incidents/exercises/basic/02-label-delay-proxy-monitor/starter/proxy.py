import numpy as np
import pandas as pd


def labeled_mae(df, now, delay_days):
    # TODO: MAE chỉ trên các dòng mà nhãn đã về lúc `now` (luật trong README); None nếu chưa có dòng nào
    raise NotImplementedError


def seasonal_baseline(daily, day, weeks=4):
    # TODO: (mean, std ddof=1) của các ngày cùng thứ trong `weeks` tuần trước `day`, bỏ ngày không có trong chỉ mục
    raise NotImplementedError


def proxy_alerts(pred_mean, fallback_rate, day, z_limit=3.0, fallback_limit=0.02, weeks=4):
    # TODO: danh sách lý do cảnh báo theo luật trong README, theo đúng thứ tự "pred_mean" rồi "fallback"
    raise NotImplementedError
