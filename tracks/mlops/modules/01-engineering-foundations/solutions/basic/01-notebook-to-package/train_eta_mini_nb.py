# %% [markdown]
# # Train ETA mini
# Notebook cũ của đồng nghiệp, xuất bằng `jupyter nbconvert --to script`. Chạy được trên máy của An,
# không chạy được ở đâu khác. Đọc để lấy logic, rồi chuyển vào package `eta_mini`; không import tệp này.

# %%
import random

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

# %%
df = pd.read_parquet("/home/an/Downloads/yellow_tripdata_2019-01.parquet")
df = df[["tpep_pickup_datetime", "tpep_dropoff_datetime", "trip_distance", "PULocationID", "DOLocationID"]]
df = df.sample(n=200_000)

# %%
df["duration_min"] = (df.tpep_dropoff_datetime - df.tpep_pickup_datetime).dt.total_seconds() / 60
df = df[(df.duration_min > 0) & (df.duration_min <= 180) & (df.trip_distance > 0) & (df.trip_distance <= 100)]

# %%
X = pd.DataFrame(
    {
        "trip_distance": df.trip_distance,
        "hour": df.tpep_pickup_datetime.dt.hour,
        "dow": df.tpep_pickup_datetime.dt.dayofweek,
        "PULocationID": df.PULocationID,
        "DOLocationID": df.DOLocationID,
    }
)
y = df.duration_min

# %%
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=random.randint(0, 1000))
model = HistGradientBoostingRegressor(max_iter=100).fit(X_train, y_train)
print("MAE", mean_absolute_error(y_test, model.predict(X_test)))

# %%
import joblib

joblib.dump(model, "C:\\Users\\an\\Desktop\\model.joblib")
