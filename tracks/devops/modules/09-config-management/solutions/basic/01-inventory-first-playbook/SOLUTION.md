# Lời giải: inventory tĩnh và playbook đầu tiên

Lời giải gồm `inventory/` (hosts, `group_vars`, `host_vars`), `site.yml` và `templates/host.ini.j2`.

## Các quyết định

- **Nhóm cha chỉ có `children`.** `olist` gom `web` và `workers`; host chỉ khai báo một lần ở nhóm lá. Play nhắm `olist` để sau này
  thêm nhóm `api` hay `batch` không phải sửa play.
- **Biến đặt ở tầng hẹp nhất đúng nghĩa.** `olist_env` chung cho mọi máy (`group_vars/all.yml`), `olist_role` và
  `olist_worker_concurrency` theo nhóm, ngoại lệ của `worker-2` ở `host_vars`. Thứ tự thắng trong inventory: `all` < nhóm cha < nhóm
  con < `host_vars`. Máy web không có biến của worker vì biến chỉ gắn vào nhóm `workers`.
- **`group_vars` cạnh inventory, không cạnh playbook.** Biến mô tả môi trường đi theo inventory (staging, prod mỗi cái một thư
  mục). `group_vars` cạnh playbook cũng được đọc và thắng `group_vars` của inventory cùng cấp, nên trộn hai chỗ là nguồn sự cố.
- **Chỉ module có trạng thái.** `group`, `user`, `file`, `template` đều so trạng thái hiện tại trước khi đổi, nên lần hai
  `changed=0` và `--check --diff` cho biết chính xác sẽ đổi gì.
- **User dịch vụ không có home thật.** `create_home: false` cùng shell `nologin`: user chỉ để sở hữu tiến trình và tệp.
- **Template dựa vào `trim_blocks`.** Dòng `{% if %}`/`{% endif %}` không để lại dòng trống, nên nội dung khớp từng byte.

## Đọc thêm

- `ansible-inventory -i inventory --graph --vars` in cây nhóm kèm biến, nhanh hơn đọc JSON.
- Inventory dạng INI vẫn phổ biến; YAML dễ đọc hơn khi có nhóm lồng và biến có cấu trúc.
- Ad-hoc tương đương một task: `ansible -i inventory workers -m ansible.builtin.user -a "name=olist system=true" --become`.
  Hữu ích khi điều tra (`-m ansible.builtin.setup -a filter=ansible_distribution*`), không thay được playbook trong Git.
