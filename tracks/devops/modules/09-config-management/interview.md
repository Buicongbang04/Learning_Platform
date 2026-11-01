# Câu hỏi phỏng vấn: configuration management với Ansible

## Idempotency là gì và làm sao bạn chứng minh một role là idempotent?

Áp cùng cấu hình lên máy đã ở trạng thái đúng thì không đổi gì và báo không đổi gì. Nó cho phép chạy lại an toàn sau sự cố, chạy định
kỳ để sửa drift, và tin chữ `changed` trong recap.

Chứng minh bằng hành vi, không bằng đọc code: converge role trên máy sạch, chạy lần hai và đòi `changed=0` (kịch bản `idempotence`
của molecule), rồi `--check --diff` cũng phải sạch. Thêm `ansible-lint` để bắt sớm mẫu xấu (`shell` thay module, `command` thiếu
`changed_when`). Thủ phạm hay gặp: `shell`/`command` không khai báo ngữ nghĩa, template có giá trị đổi mỗi lần (thời gian, thứ tự
dict), `state: latest`, `copy` với nội dung sinh ra.

## Khi nào bạn vẫn dùng `command` hay `shell`, và viết thế nào cho đúng?

Khi không có module (CLI riêng của ứng dụng, migration), hay khi chỉ đọc trạng thái để quyết định. Viết đúng nghĩa là cho Ansible
biết ngữ nghĩa của lệnh: `changed_when: false` cho lệnh chỉ đọc, `changed_when` dựa trên output cho lệnh tự báo có đổi, `failed_when`
khi mã thoát khác 0 không phải lỗi (`grep` trả 1 khi không khớp), `creates`/`removes` để bỏ qua khi đã xong (và để check mode đánh
giá đúng). Dùng `command` thay `shell` khi không cần pipe hay chuyển hướng: không có shell là không có shell injection từ biến.
`ignore_errors` không phải cách sửa: nó nuốt cả lỗi thật.

## Kể thứ tự variable precedence và một sự cố do nó gây ra.

Từ thấp tới cao, những tầng hay gặp: role `defaults` < inventory `group_vars/all` < `group_vars/<nhóm>` < `host_vars` < fact < play
`vars` < `vars_files` < role `vars` < block, task vars < `include_vars` < `set_fact`/`register` < tham số role < extra vars (`-e`, luôn
thắng). `group_vars` cạnh playbook thắng `group_vars` cạnh inventory cùng loại.

Sự cố điển hình: role đặt `log_level: INFO` trong `vars/main.yml`. Ops đặt `DEBUG` trong `group_vars` để điều tra, deploy xanh, máy vẫn
`INFO`, và `ansible-inventory --host` lại in `DEBUG` vì nó chỉ đọc inventory. Role vars (tầng 15) thắng inventory (tầng 6). Sửa: giá
trị người dùng đổi được đặt ở `defaults`; `vars` chỉ cho hằng số nội bộ. Phát hiện: task `debug` tạm trong role, hay bước verify sau
deploy đọc tệp trên máy.

## Handler chạy lúc nào? Kể hai cách handler "không chạy" mà bạn từng gặp.

Handler chạy một lần ở cuối play (hay ở `meta: flush_handlers`), theo thứ tự khai báo, chỉ khi được notify bởi task báo `changed`.

Hai cách nó không chạy: (1) task ghi tệp có `changed_when: false` (ai đó thêm để tắt màu vàng trên dashboard): tệp đổi nhưng kết quả
bị ép "không đổi", không có notify; (2) một task sau đó fail trên máy: máy bị loại khỏi play, handler đang chờ của nó bị bỏ, lần chạy
sau tệp đã đúng nên không ai notify nữa và service chạy cấu hình cũ vô thời hạn. Cách chặn: không bao giờ `changed_when: false` trên
task ghi; `force_handlers: true` cho play có restart quan trọng; health check sau deploy so cấu hình service đang dùng với tệp.

## `--check --diff` đáng tin tới đâu?

Không đổi gì trên máy và đúng với module hỗ trợ check mode. Nhưng `command`/`shell` bị bỏ qua (trừ khi có `creates`/`removes`), nên
task sau dùng kết quả của chúng nhận dữ liệu rỗng; một số module báo `changed` bảo thủ (`pip` với `extra_args` hay `requirements`);
task phụ thuộc thứ task trước sẽ tạo thì fail. `--diff` còn in nội dung tệp, nên tệp chứa bí mật phải có `diff: false`. Dùng nó để
review trước khi áp và để phát hiện drift định kỳ, không như bằng chứng tuyệt đối; task chỉ đọc cần chạy cả trong check mode thì đặt
`check_mode: false`.

## Bạn quản bí mật trong repo Ansible thế nào? Mật khẩu vault bị lộ thì làm gì?

`vars.yml` trỏ tên biến thường sang biến `vault_*`, `vault.yml` mã hoá cả tệp bằng vault id theo môi trường (`prod`, `staging`), ngoại
lệ từng giá trị bằng `encrypt_string`. Task dùng bí mật có `no_log: true` và `diff: false`. Mật khẩu vault ở secret store của CI hay
AWX, đọc qua script `--vault-id prod@client.sh`, không bao giờ trong repo. Tốt hơn nữa với bí mật động: ứng dụng đọc từ Vault hay
Secrets Manager lúc chạy, Ansible chỉ cấp quyền.

Lộ mật khẩu vault: `ansible-vault rekey` mọi tệp và giá trị inline sang mật khẩu mới, **và** xoay mọi bí mật bên trong, vì lịch sử Git
vẫn giải mã được bằng mật khẩu cũ. Kiểm log CI cũ xem có bí mật nào đã in ra do thiếu `no_log`.

## Push và pull khác nhau thế nào? Khi nào bạn dùng `ansible-pull`?

Push: máy điều khiển kết nối vào và áp cấu hình khi có người hay pipeline chạy lệnh (Ansible). Điều phối thứ tự giữa các máy dễ (rút
LB, deploy, đưa lại), không có agent; nhưng máy điều khiển phải tới được mọi máy và máy tắt lúc chạy bị lỡ. Pull: agent trên máy tự
kéo định kỳ (Puppet, Chef, `ansible-pull`): tự sửa drift, máy mới tự cấu hình, scale tốt; nhưng phải vận hành agent và khó điều phối
thứ tự.

`ansible-pull` hợp khi máy không tới được từ ngoài (sau NAT, edge) hay máy autoscaling cần tự cấu hình lúc boot qua cloud-init. Với
fleet autoscaling, tốt hơn nữa là không cấu hình nặng lúc boot: image dựng sẵn.

## Mutable hay immutable infrastructure: bạn chọn thế nào?

Câu hỏi đầu tiên: máy có giữ dữ liệu không thay được không, và máy có được tạo, huỷ tự động không. Fleet stateless, autoscaling, cần
giống hệt nhau: immutable, build image bằng Packer chạy chính role Ansible làm provisioner, đổi bản là thay máy, rollback là quay về
image cũ. Database, máy vật lý, thiết bị mạng: mutable, Ansible hay Puppet cộng phát hiện drift định kỳ. Thứ ở giữa (Nginx edge có
rule đổi hằng ngày) thường kết hợp: image nền theo tháng, cấu hình nhỏ đẩy bằng Ansible.

Cái giá của immutable: mỗi thay đổi là một lần build và rollout (vá CVE khẩn chậm hơn), cần pipeline image và dọn image cũ, và chỉ
có lợi khi máy thật sự được thay định kỳ (máy "immutable" sống hai năm cũng drift như thường nếu ai SSH vào sửa).

## Vì sao chọn Ansible thay vì Puppet, Chef hay Salt (hay ngược lại)?

Ansible: không agent (chỉ SSH, Python), YAML đọc như tài liệu, đường học thấp, mạnh ở điều phối nhiều bước theo thứ tự (rolling
deploy, migration, thiết bị mạng). Yếu: không tự sửa drift giữa hai lần chạy, chậm với hàng nghìn máy qua SSH, logic phức tạp trong
YAML/Jinja2 khó test.

Puppet hay Chef hợp khi hàng nghìn máy sống lâu phải tuân thủ liên tục: agent tự sửa drift mỗi chu kỳ, báo cáo tập trung, mô hình
khai báo có đồ thị phụ thuộc. Cái giá là vận hành server, CA, agent và học DSL (Puppet) hay Ruby (Chef). Salt nhanh nhờ ZeroMQ và có
event bus cho tự động phản ứng. Tôi chọn theo ràng buộc: số máy, máy sống lâu hay ngắn, đội có ai giữ được agent và DSL không, có cần
điều phối thứ tự không. Ở công ty đã có Puppet chạy tốt, tôi không thay bằng Ansible chỉ vì thích YAML.

## Thiết kế repo Ansible cho 3 môi trường, 5 role, 3 team cùng sửa. Bạn tổ chức thế nào?

- `inventories/{dev,staging,prod}/` mỗi cái có `hosts.yml` (hay inventory plugin), `group_vars/`, `host_vars/`, vault riêng theo vault
  id; chọn môi trường bằng `-i`, không bằng biến. Không có `group_vars` cạnh playbook để chỉ có một nguồn sự thật.
- `roles/` (hay collection nội bộ có version) mỗi role một mối quan tâm, giao diện ở `defaults` có tiền tố tên role,
  `meta/argument_specs.yml`, `molecule/` của riêng nó; `requirements.yml` ghim collection và role ngoài.
- `playbooks/` mỏng: `site.yml` gọi role theo nhóm, playbook riêng cho deploy (rolling, `serial`) và cho việc vận hành (rotate cert).
- CI: `ansible-lint`, `--syntax-check`, molecule cho role đổi, `--check --diff` trên staging và đính kèm diff vào PR; apply prod qua AWX
  hay job có phê duyệt, mật khẩu vault chỉ ở đó; Execution Environment để mọi nơi chạy cùng phiên bản.
- `CODEOWNERS` theo role và theo `inventories/prod/`; job đêm `--check` trên prod báo drift.

## Rollout bản mới cho 40 worker mà không làm sập dịch vụ: viết play thế nào?

`serial: [1, "25%"]` (canary rồi từng phần tư), `max_fail_percentage: 0`, `order: inventory`. `pre_tasks`: kiểm tham số phiên bản bằng
`assert`, rút máy khỏi load balancer bằng `delegate_to` máy LB (hay module của cloud), chờ connection draining. Deploy bản mới vào thư
mục riêng, đổi symlink, restart, `flush_handlers`, health check có `until`/`retries`. `rescue`: trỏ lại bản cũ và `fail` (máy được rescue
không bị tính là lỗi, thiếu `fail` là rollout đi tiếp với bản lỗi). `post_tasks`: đưa máy về LB. Khối deploy có `when` so bản đang
chạy với bản đích để chạy lại sau sự cố chỉ làm phần còn thiếu. Migration database chạy một lần với `run_once` trước đợt đầu, và phải
tương thích ngược với bản cũ đang chạy song song.

## Sự cố: sau deploy, 3 trong 40 worker vẫn chạy cấu hình cũ, recap xanh. Bạn điều tra thế nào?

1. Xác nhận phạm vi: ad-hoc `ansible workers -m ansible.builtin.command -a "systemctl show olist-worker -p ActiveEnterTimestamp"` và
   checksum env file trên mọi máy; tìm điểm chung của 3 máy (nhóm, AZ, đợt rollout).
2. Đọc log lần chạy (AWX, CI) cho 3 máy đó: task ghi tệp `changed` hay `ok`, handler có `RUNNING HANDLER` cho chúng không, máy có
   fail hay unreachable giữa chừng ở lần chạy trước không (handler bị bỏ khi máy fail).
3. Kiểm biến thực tế trên 3 máy: `host_vars` riêng, nhóm thêm từ inventory động, precedence (giá trị trong role `vars` thắng inventory).
4. Kiểm task có `changed_when: false` hay `when` loại trừ 3 máy; kiểm drift: ai đó sửa tay, timer khác ghi đè tệp.

Khắc phục: restart có kiểm soát (`--limit` 3 máy), rồi sửa gốc. Phòng: `force_handlers`, verify sau deploy so cấu hình service đang
dùng với tệp, CI converge hai lần, job `--check` định kỳ.

## Molecule dùng để làm gì, và nó không bắt được gì?

Molecule dựng máy test (docker, podman, Vagrant, EC2), chạy role (`converge`), chạy lại và fail nếu có `changed` (`idempotence`), rồi
`verify` trạng thái bằng Ansible hay testinfra, cuối cùng xoá máy. Chạy nhiều scenario (distro khác nhau, biến khác nhau) trong CI cho
mỗi role đổi.

Nó không bắt được: khác biệt giữa container test và máy thật (systemd, kernel, SELinux, mạng thật; role systemd thường cần container
đặc quyền hay VM), tương tác giữa các role và dữ liệu thật của môi trường, hiệu năng trên 40 máy, và mọi thứ phụ thuộc inventory thật
(precedence của biến môi trường). Vì vậy vẫn cần `--check --diff` trên staging và verify sau deploy.

## Ansible chậm với 500 máy. Bạn tối ưu những gì?

Đo trước bằng callback `profile_tasks`. Sau đó: `pipelining = True` và SSH `ControlPersist`; tăng `forks` theo CPU, RAM của control node;
`gather_facts: false` hay `gather_subset` và fact cache (Redis, jsonfile); `strategy: free` khi các máy độc lập; gom vòng lặp gói vào
một lời gọi (`apt` nhận danh sách); `async` cho task dài; tránh `delegate_to` tuần tự tới một máy. Nếu vẫn không đủ: chia inventory và
chạy song song nhiều job, chuyển phần cấu hình nặng vào image, hay cân nhắc mô hình pull cho phần cần chạy liên tục.
