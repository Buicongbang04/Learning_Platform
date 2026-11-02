# Lời giải: đọc model card và config.json

## Cách làm

**`read_frontmatter`**: tách dòng, dòng đầu phải là `---`, tìm dòng `---` kế tiếp, `yaml.safe_load` phần giữa. Kết
quả không phải dict (frontmatter rỗng cho `None`) thì trả `{}`. Dùng `safe_load`, không `load`: model card là nội dung
do người khác viết, `yaml.load` với loader đầy đủ có thể dựng object Python tuỳ ý.

**`count_params`** cộng từng khối theo quy tắc của đề:

$$
N = L\big(\underbrace{h\,n_q d + 2h\,n_{kv} d + n_q d\,h}_{\text{q, k, v, o}} + \text{bias} + \text{qk-norm} + \text{MLP} + 2h\big) + h + V h\,(1 + [\text{không tied}])
$$

với MLP dense là $$3h \cdot$$ `intermediate_size`, MoE là $$E \cdot 3h \cdot$$ `moe_intermediate_size` $$+ h E_{\text{tổng}}$$
(router), $$E$$ là tổng số expert hoặc `num_experts_per_tok` khi `active=True`.

Cách kiểm độc lập mà không tải trọng số: dựng model trên device `meta` (chỉ có shape, không cấp bộ nhớ) rồi đếm.
Lời giải mẫu đã đối chiếu như vậy với `transformers` 5.22.0 cho cả 7 config, khớp từng tham số:

```python
import torch
from transformers import AutoConfig, AutoModelForCausalLM

cfg = AutoConfig.from_pretrained("Qwen/Qwen2.5-3B-Instruct")  # chỉ tải config.json
with torch.device("meta"):
    model = AutoModelForCausalLM.from_config(cfg)
print(sum(p.numel() for p in model.parameters()))  # 3085938688
```

**`weights_gb`, `kv_cache_gb`** là công thức mục 4 lý thuyết. **`fits_on_gpu`** dùng `count_params(config)` (tổng),
không phải `active=True`: mọi expert phải nằm trong VRAM vì token nào cũng có thể được route tới bất kỳ expert nào.

**`card_summary`**: `license: other` là tín hiệu phải đọc `license_name` và `license_link`; `base_model` có model card
ghi chuỗi, có model card ghi danh sách (SmolLM2, Qwen3-0.6B).

## Số liệu của 7 model

| Model | Tham số | Hoạt động | Giấy phép | Context | bf16 | 4 bit | Vừa 4GB (4 bit, 4 096 token) | Vừa 12GB (4 bit) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Qwen2.5-0.5B-Instruct | 494 032 768 | = | apache-2.0 | 32 768 | 0.99 GB | 0.25 GB | có | có |
| Qwen2.5-3B-Instruct | 3 085 938 688 | = | **qwen-research** | 32 768 | 6.17 GB | 1.54 GB | có | có |
| Qwen2.5-7B-Instruct | 7 615 616 512 | = | apache-2.0 | 32 768 | 15.23 GB | 3.81 GB | không (4.54 GB) | có |
| Qwen3-0.6B | 596 049 920 | = | apache-2.0 | 40 960 | 1.19 GB | 0.30 GB | có | có |
| Qwen3-30B-A3B-Instruct-2507 | 30 532 122 624 | 3 353 032 704 | apache-2.0 | 262 144 | 61.06 GB | 15.27 GB | không | **không** |
| SmolLM2-360M-Instruct | 361 821 120 | = | apache-2.0 | 8 192 | 0.72 GB | 0.18 GB | có | có |
| Mistral-7B-Instruct-v0.3 | 7 248 023 552 | = | apache-2.0 | 32 768 | 14.50 GB | 3.62 GB | không (4.66 GB) | có |

Trả lời câu hỏi cuối đề:

- **Qwen2.5-7B trên 12GB**: bf16 cần 15.2 GB chỉ riêng trọng số, không vừa. 4 bit cần khoảng 4.5 GB, vừa thoải mái, còn
  chỗ cho context dài hoặc nhiều request. Trên laptop 4GB thì không, kể cả 4 bit: phải dùng 3B hoặc nhỏ hơn, hoặc để một
  phần layer trên CPU (Ollama tự làm vậy, nhưng chậm hẳn).
- **Qwen3-30B-A3B**: compute mỗi token như model 3B, nhưng 15.3 GB trọng số 4 bit không vừa 12 GB. "A3B" là chuyện tốc
  độ, không phải bộ nhớ. Muốn chạy phải offload một phần expert ra RAM (128 GB RAM của PC làm được, chậm hơn).
- **Giấy phép**: chỉ Qwen2.5-3B-Instruct dùng `qwen-research`, tệp LICENSE ghi rõ "FOR NON-COMMERCIAL PURPOSES ONLY",
  dùng thương mại phải xin phép Alibaba Cloud. Đây đúng là model `qwen2.5:3b` track dùng trên laptop: hợp lệ cho học tập,
  nhưng sản phẩm thương mại phải chọn bản 1.5B hoặc 7B (Apache-2.0) hay model khác. Hai model cùng họ, cùng ngày phát
  hành, khác giấy phép: chỉ đọc tên họ model là không đủ.

## Bẫy thường gặp

- Tin `num_parameters` ghi trong tên model: "7B" của Qwen2.5 là 7.62 tỉ, "7B" của Mistral là 7.25 tỉ. Tính VRAM bằng
  số thật.
- Dùng $$h / n_q$$ khi config có `head_dim`: Qwen3-0.6B ra KV cache và attention sai một nửa.
- Tính KV cache với $$n_q$$ thay vì $$n_{kv}$$: Qwen2.5-3B có 16 head query nhưng chỉ 2 head KV (GQA), KV cache thật nhỏ
  hơn 8 lần con số sai.
- Dùng số tham số hoạt động của MoE để tính VRAM.
- Đọc `license` mà bỏ qua `other`: giá trị `other` không phải "giấy phép tự do".
