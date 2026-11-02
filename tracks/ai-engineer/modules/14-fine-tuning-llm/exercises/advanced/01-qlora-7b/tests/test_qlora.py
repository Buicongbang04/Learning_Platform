import re

import pytest
import torch

from testkit import Exercise

ex = Exercise(__file__)

QWEN_05B = {"hidden_size": 896, "intermediate_size": 4864, "num_attention_heads": 14, "num_key_value_heads": 2,
            "num_hidden_layers": 24, "vocab_size": 151936, "tie_word_embeddings": True}
QWEN_7B = {"hidden_size": 3584, "intermediate_size": 18944, "num_attention_heads": 28, "num_key_value_heads": 4,
           "num_hidden_layers": 28, "vocab_size": 152064, "tie_word_embeddings": False}
ALL = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


@pytest.fixture(scope="module")
def nb():
    return ex.notebook("qlora.ipynb")


def test_lora_param_count_matches_peft_numbers(nb):
    assert nb.lora_param_count(QWEN_05B, 16, ALL) == 8_798_208
    assert nb.lora_param_count(QWEN_05B, 8, ["q_proj", "v_proj"]) == 540_672
    assert nb.lora_param_count(QWEN_7B, 16, ALL) == 40_370_176
    assert nb.lora_param_count(QWEN_7B, 64, ["q_proj", "v_proj"]) == 20_185_088
    assert nb.lora_param_count({**QWEN_05B, "head_dim": 128}, 4, ["k_proj"]) == 24 * 4 * (896 + 2 * 128)


def test_weight_memory(nb):
    bf16 = nb.weight_memory_gib(QWEN_05B, 16)
    assert bf16 * 2**30 * 8 / 16 == pytest.approx(494_032_768), "bf16: đúng tổng số tham số của Qwen2.5-0.5B × 2 byte"
    nf4 = nb.weight_memory_gib(QWEN_05B, 4.127)
    linear = 24 * (2 * 896 * 896 + 2 * 896 * 128 + 3 * 896 * 4864)
    other = 494_032_768 - linear
    assert nf4 == pytest.approx((linear * 4.127 + other * 16) / 8 / 2**30)
    untied = nb.weight_memory_gib(QWEN_7B, 16) * 2**30 * 8 / 16
    assert untied == pytest.approx(7_615_616_512), "7B không dùng chung embedding với lm_head"


def test_bnb_config(nb):
    cfg = nb.bnb_4bit_config()
    assert cfg.load_in_4bit and not cfg.load_in_8bit
    assert cfg.bnb_4bit_quant_type == "nf4"
    assert cfg.bnb_4bit_use_double_quant is True
    assert cfg.bnb_4bit_compute_dtype == torch.bfloat16


def test_qlora_sft_kwargs(nb):
    kw = nb.qlora_sft_kwargs("/tmp/out", batch_size=2, grad_accum=8, lr=1e-4, epochs=2)
    assert kw["optim"] == "paged_adamw_8bit" and kw["gradient_checkpointing"] is True and kw["bf16"] is True
    assert (kw["per_device_train_batch_size"], kw["gradient_accumulation_steps"]) == (2, 8)
    assert kw["learning_rate"] == 1e-4 and kw["num_train_epochs"] == 2 and kw["output_dir"] == "/tmp/out"
    assert kw["max_length"] == 256 and kw["report_to"] == [] and kw["save_strategy"] == "no"
    assert kw["dataloader_num_workers"] == 0 and kw["seed"] == 0


def test_pasted_helpers(nb):
    assert nb.parse_output('{"sentiment": "neutral", "topic": "others"}') == ("neutral", "others")
    assert nb.parse_output('```json\n{"sentiment": "neutral", "topic": "others"}\n```') is None
    assert nb.to_chat("x", "positive", "lecturer")[-1]["content"] == '{"sentiment": "positive", "topic": "lecturer"}'
    assert nb.macro_f1(["a", "b", "b"], ["a", "b", None], ["a", "b"]) == pytest.approx((1 + 2 / 3) / 2)


def test_report_written():
    doc = ex.read("REPORT.md")
    assert "TODO" not in doc
    assert len(doc.split()) >= 400, "báo cáo: ít nhất 400 từ"
    assert re.search(r"^\|.*\|\s*$", doc, re.M), "cần bảng số liệu"
