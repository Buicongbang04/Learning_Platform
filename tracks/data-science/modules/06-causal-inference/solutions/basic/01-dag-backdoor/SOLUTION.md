# Lời giải: DAG, d-separation và backdoor criterion

## Ba khối cơ bản quyết định mọi thứ

| Khối | Hình | Không điều kiện | Điều kiện trên M (hoặc C) |
| --- | --- | --- | --- |
| Chain | X → M → Y | Mở: thông tin chảy qua M | Chặn |
| Fork | X ← M → Y | Mở: M là nguyên nhân chung (confounder) | Chặn |
| Collider | X → C ← Y | **Chặn**: hai nguyên nhân độc lập | **Mở**, kể cả khi chỉ điều kiện trên hậu duệ của C |

Một đường đi bị chặn nếu **một** khối trên đường bị chặn. X và Y d-separated khi mọi đường giữa
chúng bị chặn.

## Vì sao thuật toán moral ancestral graph đúng

Liệt kê mọi đường đi rồi xét từng khối thì đúng nhưng chậm và dễ sai ở trường hợp hậu duệ của
collider. Thuật toán của Lauritzen gói cả ba khối vào thao tác đồ thị:

1. Chỉ giữ tổ tiên của x, y, z. Một collider không thuộc tập này (không ai điều kiện trên nó hay
   hậu duệ của nó) bị bỏ đi, nên đường qua nó tự đứt: đúng quy tắc "collider tự chặn".
2. Moralize: nối các cha chung con. Nếu collider `C` (hoặc hậu duệ của nó) nằm trong z, `C` thuộc
   tập tổ tiên, nên hai cha của `C` được nối trực tiếp; xoá `C` cũng không cắt được cạnh này:
   đúng quy tắc "điều kiện trên collider mở đường".
3. Xoá z rồi xét liên thông: chain và fork đi qua một node trong z bị cắt.

## Backdoor criterion

Bỏ các cạnh đi ra từ treatment thì mọi đường còn nối treatment với outcome đều là đường "đi cửa
sau" (bắt đầu bằng mũi tên đi **vào** treatment). Tập z chặn hết chúng mà không chứa hậu duệ của
treatment thì `E[Y | do(T)]` tính được bằng điều chỉnh theo z.

Điều kiện "không chứa hậu duệ" loại hai lỗi rất hay gặp:

- **Điều chỉnh mediator** (`contact_cs` trong DAG Olist): cắt mất phần tác động đi qua mediator,
  nên ước lượng không còn là tác động tổng.
- **Điều chỉnh collider là hậu duệ** (C trong `COLLIDER`): mở một đường giả giữa T và Y.

M-bias cho thấy thêm: M **không** phải hậu duệ của T, nhưng là collider giữa A và B. Điều chỉnh
riêng M mở đường T ← A → M ← B → Y; điều chỉnh thêm A hoặc B thì đóng lại. "Cứ cho mọi biến tiền
xử lý vào hồi quy" vì thế không phải lúc nào cũng an toàn, dù trong thực tế M-bias thường nhỏ.

## Con số trong mô phỏng

Tác động thật là 2.0. Qua 30 seed:

- Confounder: không điều chỉnh cho trung bình 3.39 (lệch +70%); điều chỉnh Z thì sai số lớn nhất
  0.023.
- Collider: không điều chỉnh thì đúng (sai số lớn nhất 0.016); điều chỉnh C kéo ước lượng về
  khoảng 0.50, tức **mất ba phần tư tác động** chỉ vì thêm một biến "có vẻ liên quan".

## Trong thực tế

DAG không đến từ dữ liệu mà từ hiểu biết về nghiệp vụ: phải hỏi đội vận hành vì sao đơn trễ, hỏi
đội CSKH khách phàn nàn ra sao. Giá trị của DAG là buộc mọi giả định thành **hình vẽ có thể tranh
luận**, thay vì ẩn trong danh sách biến của một câu lệnh hồi quy. Thư viện `DoWhy` và `dagitty`
làm phần thuật toán; phần khó là vẽ đúng DAG.
