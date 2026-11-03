# Repo `eta-service-v0` (người viết đã nghỉ việc)

Repo nội bộ của dự án dự đoán thời gian chạy xe, đang phục vụ một API nhỏ. Bạn nhận lại nó. Không ai nhớ vì sao
mọi thứ được làm như vậy. Đây là cây thư mục và vài đoạn trích; mọi dòng ghi ở đây là sự thật của repo.

```text
eta-service-v0/
├── README.md
├── requirements.txt
├── config.py
├── train.py
├── utils.py
├── app.py
├── data/
│   ├── trips_2019_01.parquet
│   └── trips_2019_01_clean_v2.parquet
├── models/
│   ├── model_v7.pkl
│   └── model_v7_final.pkl
├── notebooks/
│   └── final_FINAL_v3.ipynb
└── tests/
    └── __init__.py
```

## Số liệu từ `git`

- `git count-objects -vH` báo 1,9 GiB; `data/*.parquet` và `models/*.pkl` nằm trong lịch sử từ commit đầu tiên.
- 41 commit, 38 commit có message `update` hoặc `fix`.
- Không có `.gitignore`, không có CI, không có `Makefile`, `tests/` chỉ có `__init__.py` rỗng.

## Trích đoạn

`README.md`:

```text
Chạy: mở notebooks/final_FINAL_v3.ipynb, Run All, rồi copy model_v7_final.pkl sang server.
Python 3.8 (đừng dùng bản khác, bị lỗi).
```

`requirements.txt`:

```text
pandas
scikit-learn
flask
xgboost
```

`config.py`:

```python
DATA_PATH = "/home/hieu/Downloads/trips_2019_01.parquet"
MODEL_PATH = "/srv/eta/model_v7_final.pkl"
DB_URL = "postgresql://admin:Eta2019!@10.0.3.14:5432/prod"
```

`train.py`:

```python
import sys
sys.path.append("..")
from utils import *
df = pd.read_parquet(DATA_PATH)
df = df.sample(frac=0.3)
X_train, X_test = train_test_split(df)
model = XGBRegressor().fit(X_train[cols], X_train.y)
pickle.dump(model, open(MODEL_PATH, "wb"))
print("done")
```

`app.py`:

```python
model = pickle.load(open(MODEL_PATH, "rb"))

@app.route("/eta")
def eta():
    row = request.args.to_dict()
    return str(model.predict(pd.DataFrame([row]))[0])
```

`utils.py` (1 240 dòng): chứa `build_features` (có đoạn `df["hour"] = df.pickup.dt.hour` lặp lại 3 lần, mỗi lần một
kiểu), `clean`, `plot_everything`, `send_slack`, và hằng `cols = [...]` được `from utils import *` kéo vào cả `train.py` lẫn `app.py`.
`notebooks/final_FINAL_v3.ipynb`: 74 cell, có output 52 MB, cell 31 sửa `df.trip_distance` tại chỗ, cell 48 train
model bằng tham số khác với `train.py`.
