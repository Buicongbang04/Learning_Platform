# Thiết kế lớp edge cho Olist Shop production

## 4. Firewall và security group

| Nguồn | Đích | Cổng | Giao thức | Lý do |
| --- | --- | --- | --- | --- |
| 0.0.0.0/0 | ALB | 443 | TCP | HTTPS công khai |
| 0.0.0.0/0 | ALB | 80 | TCP | Chuyển hướng sang HTTPS |
| sg-alb | sg-edge | 80 | TCP | ALB tới Nginx |
| 0.0.0.0/0 | sg-db | 5432 | TCP | Cho tiện kết nối từ máy dev |
| 0.0.0.0/0 | sg-edge | 22 | TCP | SSH quản trị |
