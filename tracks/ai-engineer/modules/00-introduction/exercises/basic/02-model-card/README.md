---
title: Đọc model card và config.json - giấy phép, số tham số, VRAM
level: basic
services: []
files:
  - path: starter/model_card.py
    note: 6 hàm TODO
  - path: tests/fixtures/
    note: config.json và frontmatter model card thật của 7 model
  - path: tests/test_model_card.py
    note: Không sửa
run:
  - uv run pytest tracks/ai-engineer/modules/00-introduction/exercises/basic/02-model-card -q
---

## Mục tiêu

Trước khi đưa một model mở vào sản phẩm, AI Engineer đọc hai tệp: **model card** (giấy phép, model gốc, mục đích) và
**`config.json`** (kiến trúc). Làm xong bài này bạn tự đếm được số tham số tới từng đơn vị chỉ từ config, biết model có
vừa GPU của mình không, và không bị bẫy giấy phép "cùng họ model nhưng khác điều khoản".

## Đề bài

**Phần cứng:** CPU · ~50 phút

`tests/fixtures/<tổ chức>__<model>/` chứa `config.json` và phần frontmatter YAML của `README.md` (model card) tải từ
Hugging Face ngày 2026-10-30 cho 7 model: Qwen2.5 0.5B, 3B, 7B Instruct; Qwen3-0.6B; Qwen3-30B-A3B-Instruct-2507 (MoE);
SmolLM2-360M-Instruct (kiến trúc Llama); Mistral-7B-Instruct-v0.3. Mở vài tệp ra đọc trước. Đọc mục 4 lý thuyết
(bộ nhớ: trọng số và KV cache).

Trong `starter/model_card.py`, chỉ dùng thư viện chuẩn và `yaml`, **không dùng `transformers`**, viết:

1. `read_frontmatter(text) -> dict`: YAML giữa dòng `---` đầu tiên (phải là dòng đầu tệp) và dòng `---` kế tiếp. Không
   có hoặc rỗng thì `{}`.
2. `count_params(config, active=False) -> int`: đếm **đúng từng tham số** như PyTorch đếm, theo các quy tắc sau. Gọi
   $$h$$ = `hidden_size`, $$n_q$$ = `num_attention_heads`, $$n_{kv}$$ = `num_key_value_heads` (thiếu thì bằng $$n_q$$),
   $$d$$ = `head_dim` nếu config có và khác `null`, ngược lại $$h / n_q$$; $$V$$ = `vocab_size`.
   - Embedding $$V \cdot h$$. LM head thêm $$V \cdot h$$ nữa, trừ khi `tie_word_embeddings` là `true` (dùng chung ma
     trận embedding). Một RMSNorm cuối có $$h$$ tham số.
   - Mỗi layer có hai RMSNorm ($$h$$ mỗi cái) và attention gồm 4 ma trận không bias: q ($$h \times n_q d$$), k và v
     ($$h \times n_{kv} d$$ mỗi cái), o ($$n_q d \times h$$).
   - Bias attention: `model_type` là `qwen2` thì q, k, v có bias (o không). Model khác có `attention_bias: true` thì cả
     q, k, v, o có bias. `qwen3` và `qwen3_moe` có thêm hai RMSNorm trên từng head (q_norm, k_norm), $$d$$ tham số mỗi cái.
   - MLP dense (gate, up, down, không bias): $$3 \cdot h \cdot$$ `intermediate_size`.
   - MoE (config có `num_experts`): mỗi layer có `num_experts` expert, mỗi expert là một MLP với
     `moe_intermediate_size`, cộng một router tuyến tính $$h \times$$ `num_experts` không bias. Với `active=True` chỉ tính
     `num_experts_per_tok` expert mỗi layer (router vẫn tính đủ). Model dense thì `active` không đổi kết quả.
3. `weights_gb(n_params, bits) -> float`: GB = $$10^9$$ byte.
4. `kv_cache_gb(config, seq_len, batch=1, bytes_per_value=2) -> float`: công thức ở mục 4 lý thuyết.
5. `fits_on_gpu(config, vram_gb, bits, seq_len, batch=1, overhead_gb=0.5) -> bool`: trọng số của **mọi** tham số ở
   `bits` bit, cộng KV cache 2 byte mỗi giá trị, cộng `overhead_gb`, không vượt `vram_gb`.
6. `card_summary(readme_text, config) -> dict`: các khoá `license` (giá trị `license`; nếu là `"other"` thì lấy
   `license_name`), `base_model` (chuỗi; frontmatter ghi danh sách thì lấy phần tử đầu; không có thì `None`), `params`,
   `active_params`, `context_length` (`max_position_embeddings`), `moe`.

Rồi trả lời cho chính mình: Qwen2.5-7B-Instruct có chạy được trên GPU 12GB của PC ở bf16 không, ở 4 bit thì sao? Trên
laptop 4GB? Qwen3-30B-A3B "chỉ 3B hoạt động" có vừa 12GB ở 4 bit không? Model nào trong 7 model **không** dùng thương
mại tự do được?

## Tiêu chí đạt

- `count_params` khớp **chính xác** số đếm của `transformers` cho cả 7 config: 494 032 768 (Qwen2.5-0.5B) tới
  30 532 122 624 (Qwen3-30B-A3B), và 3 353 032 704 tham số hoạt động của Qwen3-30B-A3B.
- Thêm `attention_bias: true` vào config Llama tăng đúng số bias của q, k, v, o; bỏ tied embedding tăng đúng $$V \cdot h$$.
- `kv_cache_gb` của Qwen2.5-3B với 4 096 token là 0.151 GB; Qwen3-0.6B dùng `head_dim` 128 của config.
- `fits_on_gpu` trả đúng cho các trường hợp trong test, kể cả MoE (phải chứa mọi expert).
- `card_summary` của Qwen2.5-3B-Instruct cho `license == "qwen-research"`.

## Gợi ý

### Gợi ý 1

Viết `count_params` từng phần và in ra cho Qwen2.5-0.5B: embedding 151 936 × 896 = 136 134 656 phải chiếm 27.6% tổng
494 032 768. Sai một chút thường do: quên bias q, k, v của Qwen2; tính lm_head khi embedding đã tied; dùng
$$h / n_q$$ thay cho `head_dim` của Qwen3 (1 024 / 16 = 64, nhưng config ghi 128); dùng $$n_q$$ cho k, v thay vì
$$n_{kv}$$ (GQA).

### Gợi ý 2

Hiệu giữa số của bạn và số đúng chia cho `num_hidden_layers` thường ra một con số quen: $$2h$$ (quên hai RMSNorm),
$$n_q d + 2 n_{kv} d$$ (quên bias), $$2d$$ (quên q_norm, k_norm). Với MoE, router có `num_experts` cột kể cả khi
`active=True`: token phải qua router để chọn expert. Với frontmatter, `yaml.safe_load` của chuỗi rỗng trả `None`.
