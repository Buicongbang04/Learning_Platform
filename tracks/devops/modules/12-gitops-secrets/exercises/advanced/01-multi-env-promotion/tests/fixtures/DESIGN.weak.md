# Thiết kế GitOps cho Olist Shop

## 1. Bối cảnh và ràng buộc

Có hai môi trường: staging và production, mỗi môi trường một namespace trên cùng cluster.

## 2. Cấu trúc repo

Mỗi môi trường một nhánh: nhánh `staging` và nhánh `production`, mỗi nhánh có một bản base và overlay riêng, app-of-apps ở nhánh main.

```text
envs/
  staging/
  production/
```

## 3. Quy trình promote

Merge nhánh staging vào nhánh production khi thấy ổn.

- Dev merge vào staging.
- Kiểm tay trên staging.

## 4. Ai được làm gì

- Mọi người trong team đều push được lên production cho nhanh.

## 5. Secret theo môi trường

Secret dùng SOPS, mỗi môi trường một khoá.

## 6. Rollback và drift

- Sửa tay bằng kubectl edit khi cần gấp.

## 7. Đánh đổi đã cân nhắc

- Dùng branch cho môi trường, không dùng Helm.
