# Lời giải: train không tái lập

## Nguyên nhân

Có ba nguồn, và sửa riêng lẻ chỉ che một phần:

1. **`random.shuffle` trong `split`** dùng module `random` của Python, không phải `np.random`. `np.random.seed(seed)` ở đầu hàm làm người đọc tưởng đã gieo hạt, nhưng việc chia train/test vẫn lấy ngẫu nhiên từ trạng thái không ai kiểm soát. Đây là "seed rò": seed có mặt nhưng không bao phủ mọi nguồn.
2. **`os.listdir` không đảm bảo thứ tự.** Thứ tự phụ thuộc hệ tệp (ext4 theo hash, tmpfs theo thời gian tạo, ổ mạng theo cách khác), nên cùng thư mục cho DataFrame có thứ tự dòng khác nhau trên hai máy. Chia theo vị trí dòng sẽ cho tập test khác nhau dù seed giống nhau.
3. **Gieo hạt toàn cục thay vì cục bộ.** `np.random.seed` trong thư viện làm đổi trạng thái của cả chương trình gọi: chạy hai pipeline trong cùng một tiến trình ảnh hưởng lẫn nhau.

## Cách sửa

```python
def load_trips(data_dir):
    paths = sorted(Path(data_dir).glob("*.csv"))
    return pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)

def split(df, seed, test_fraction=0.2):
    order = np.random.default_rng(seed).permutation(len(df))
    ...

model = RandomForestRegressor(n_estimators=30, n_jobs=1, random_state=seed)
```

## Vì sao test viết như vậy

- Ca "hai lần chạy" đổi trạng thái `random` và `np.random` giữa hai lần: bắt nguồn ngẫu nhiên không nằm dưới `seed`.
- Ca "thứ tự liệt kê" thay `os.listdir` bằng bản trả thứ tự khác: tái hiện hai máy khác nhau mà không cần hai máy.
- Ca "seed vẫn có tác dụng": chặn cách sửa cẩu thả (cố định cứng một số) làm hết biến thiên.
- Ca "không đụng trạng thái toàn cục": hợp đồng của một hàm thư viện.

## Bài học vận hành

Khi ai đó báo "chạy hai lần ra khác nhau": (1) tìm mọi nơi gọi bộ sinh ngẫu nhiên, (2) tìm mọi chỗ phụ thuộc thứ tự (listdir, glob, set, dict từ nguồn ngoài, `groupby` không sort, đọc song song), (3) kiểm tra phiên bản thư viện và số luồng. Với dữ liệu thật thêm: dữ liệu đầu vào có đổi giữa hai lần không (hash tệp, `dvc.lock`, module 03).

## Lỗi hay gặp

- Gieo `random.seed`, `np.random.seed` và `torch.manual_seed` cùng lúc ở đầu `main` rồi coi là xong: không bao phủ thứ tự tệp, đa luồng, và làm đổi trạng thái toàn cục.
- Sort theo giá trị cột có trùng khoá (ties): thứ tự không xác định trở lại. Cần khoá phụ duy nhất.
- Chỉ so MAE bằng `==` giữa các phiên bản thư viện khác nhau; tái lập tuyệt đối đòi cùng phiên bản và số luồng.
